from datetime import datetime, time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Min, Value, Q, Count, Sum, F
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, ListView
from django.views.generic.base import ContextMixin, TemplateResponseMixin

from app.models import Customer, Sale, SaleProduct, SaleInstallment
from app.models import KeyValueStore
from app.views import FilterSetView
from collection.models import Collection, CollectionInstallment, CollectorSyncLog

from collection.forms import CollectionFormset, CollectionFilterForm

from silk.profiling.profiler import silk_profile


class CollectionData:
    sales_with_pending_balance = None

    def get_installments_detail(self):
        data = dict()

        for s in self.sales_with_pending_balance:
            if not data.get(s['customer']):
                data[s['customer']] = dict()

            installments = SaleInstallment.objects.\
                filter(sale=s['pk']).\
                filter(Q(status=SaleInstallment.PARTIAL) | Q(status=SaleInstallment.PENDING)).\
                order_by('sale', 'installment', 'status').\
                values('pk', 'sale_id', 'status', 'installment', 'installment_amount', 'paid_amount')

            data[s['customer']][s['pk']] = {
                'id': s['pk'],
                'installments': list(installments)
            }

        return data

    def set_sales_with_pending_balance(self, customer=None):
        user = self.request.user
        # If user is admin get all sales (no filter)
        if user.is_admin:
            q_filter = Q()
        else:
            # If user is not an admin, and customer is not None
            if customer:
                customer_record = Customer.objects.get(id=customer)
                # If customer collector is the current user then get all customer sales
                # If customer collector is not the current user then get all customer sales whose collector
                # is the current user
                if customer_record.collector == user:
                    q_filter = Q(customer=customer)
                else:
                    q_filter = Q(customer=customer, collector=user)
            else:
                # If customer is None then get sales of customers whose collector is the current user
                # and get whose collector is the current user but the customer collector is not the current user
                q_filter = Q(customer__collector=user) | Q(~Q(customer__collector=user), collector=user)

        self.sales_with_pending_balance = self.get_pending_sales(q_filter, ['pk', 'customer'])

    def get_sales_detail(self, customer=None):
        data = dict()
        self.set_sales_with_pending_balance(customer)

        for s in self.sales_with_pending_balance:
            if not data.get(s['customer']):
                data[s['customer']] = []

            sale = Sale.objects.get(pk=s['pk'])
            products = SaleProduct.objects.filter(sale=s['pk']).values('product__name')

            temp = {
                'id': sale.pk,
                'installments': sale.installments,
                'date': sale.date,
                'price': sale.price,
                'paid_amount': sale.paid_amount,
                'pending_balance': sale.pending_balance,
                'products': [p['product__name'] for p in products]
            }

            data[s['customer']].append(temp)
        return data

    def get_data(self, customer=None):
        sales = self.get_sales_detail(customer)
        installments = self.get_installments_detail()

        data = {
            'sales': sales,
            'installments': installments
        }

        return data

    def get_customers(self, user):
        # If the user is not an admin then filter collections by loggued user
        if not user.is_admin:
            # Customers assigned to the current user
            collector_customers = Customer.objects.filter(collector=user)
            # Sales whose collection is assigned to the current collector
            sales_id = self.get_pending_sales(Q(collector=user), ['customer'])

            filters = Q()
            for id in sales_id:
                filters |= Q(id=id['customer'])
            sales_customers = Customer.objects.filter(filters)
            # Join customer querysets and discard repeated
            customers = collector_customers.union(sales_customers).values('pk', 'name')
        else:
            customers = Customer.objects.values('pk', 'name')

        return customers

    def get_pending_sales(self, filters, fields):
        return Sale.objects.\
            filter(filters).\
            annotate(paid_installments=Count('saleinstallment__pk', filter=Q(saleinstallment__status='PAID'))).\
            exclude(installments=F('paid_installments')).\
            values(*fields)

    def collector_validation(self, customer, user):
        # Valid customer validation
        customer_record = Customer.objects.get(id=customer)
        if not customer_record:
            raise Http404

        # If the current collector is not an admin
        # Raise a 403 error if the selected customer is not assigned to the collector
        if not user.is_admin:
            if customer_record.collector != user:
                sales_whose_collector_is_user = self.get_pending_sales(Q(customer=customer, collector=user), ['pk'])
                if sales_whose_collector_is_user.count() == 0:
                    raise PermissionDenied

        return True


class ServiceWorkerView(TemplateView):
    template_name = 'sw.js'
    content_type = 'application/javascript'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['version'] = '0.2'
        return context


class ManifestView(TemplateView):
    template_name = 'manifest.json'
    content_type = 'application/json'


class OfflineView(TemplateView):
    template_name = 'offline.html'


class CollectionCreationView(LoginRequiredMixin, ContextMixin, TemplateResponseMixin, CollectionData, View):
    template_name = 'create_collection.html'
    collector = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.collector = self.request.user
        context['customers'] = self.get_customers(self.collector)
        context['formset'] = CollectionFormset(prefix='collection')
        return context

    @silk_profile(name='Collection Get')
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        selected_customer_param = self.request.GET.get('select-customer', None)
        selected_customer = int(selected_customer_param) if selected_customer_param is not None else selected_customer_param

        if selected_customer:
            if self.collector_validation(selected_customer, self.collector):
                # get_data return sales and installments data
                data = self.get_data(selected_customer)
                data['customers'] = list(context['customers'])
                data['selected_customer'] = selected_customer
                context['selected_customer'] = selected_customer

                return JsonResponse(data)
            else:
                # Add this exception as a default behavior if collector_validation didn't catch any error
                raise PermissionDenied
        else:
            return self.render_to_response(context)

    @silk_profile(name='Collection Post')
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        selected_customer = request.POST.get('customer', None)
        customer = Customer.objects.get(id=selected_customer)
        if customer:
            # If the current collector is not an admin
            # Raise a 403 error if the selected customer is not assigned to the collector
            if not self.collector.is_admin:
                if customer.collector != self.collector:
                    raise PermissionDenied

            collection_formset = CollectionFormset(
                self.request.POST,
                prefix='collection'
            )
            # If there is an exception commits are rolled back
            with transaction.atomic():
                collection = None
                # In this list I will save already checked sales
                sales_check_collection = []
                # To sum the total paid amount and prevent saving empty collections
                check_total = 0

                for f_form in collection_formset:
                    # If form has changed the field "checked" then it is being paid
                    if 'checked' in f_form.changed_data:
                        # Check if form is valid or not
                        if f_form.is_valid():
                            data = f_form.cleaned_data

                            check_total += data['amount']

                            # Check that the sale corresponds to the selected customer
                            if not data['sale_id'] in sales_check_collection:
                                sale = Sale.objects.get(id=data['sale_id'])
                                if sale.customer != customer:
                                    raise PermissionDenied
                                # Add the sale to the list to prevent check it again if there are
                                # more than one paid installment
                                sales_check_collection.append(data['sale_id'])

                            # If collection record has not being created
                            if not collection:
                                collection = Collection(
                                    collector=request.user,
                                    customer=customer
                                )
                                collection.save()

                            # Create collection installment record
                            sale_installment = SaleInstallment.objects.get(
                                sale=data['sale_id'],
                                installment=data['installment']
                            )
                            collection_installment = CollectionInstallment(
                                collection=collection,
                                sale_installment=sale_installment,
                                amount=data['amount']
                            )
                            collection_installment.save()

                            # Update the paid amount and the status from the sale installment record
                            installment_amount = sale_installment.installment_amount
                            paid_amount = sale_installment.paid_amount
                            if installment_amount > paid_amount + data['amount']:
                                sale_installment.status = SaleInstallment.PARTIAL
                            else:
                                sale_installment.status = SaleInstallment.PAID
                            sale_installment.paid_amount = F('paid_amount') + data['amount']
                            sale_installment.save()
                        else:
                            # If form has errors
                            print(f_form.errors)
                if check_total == 0:
                    raise ValidationError('El total pagado debe ser mayor a cero')

        response_data = {}
        response_data['collection_id'] = collection.pk

        return JsonResponse(response_data)


class CollectionListView(LoginRequiredMixin, ListView, FilterSetView):
    template_name = 'list_collection.html'
    context_object_name = 'collections'
    filterset = [
        ('collector', 'collector', 'exact'),
        ('customer', 'customer', 'exact'),
        ('date_from', 'date', 'gte'),
        ('date_to', 'date', 'lte'),
    ]

    def get_queryset(self):
        filters = self.get_filters(self.request)
        if filters:
            queryset = Collection.objects.\
                filter(filters).\
                prefetch_related('collectioninstallment_set').\
                annotate(paid_amount=Sum('collectioninstallment__amount')).\
                order_by('-pk').\
                all()
        else:
            today = datetime.today().date()
            tz = timezone.get_current_timezone()
            # Else add 00:00:00 (start of the day)
            date_start = datetime.combine(today, time.min)
            value = timezone.make_aware(date_start, tz, False)

            queryset = Collection.objects.\
                filter(date__gte=value).\
                prefetch_related('collectioninstallment_set').\
                annotate(paid_amount=Sum('collectioninstallment__amount')).\
                order_by('-pk').\
                all()

        # If the user is not an admin then filter collections by loggued user
        user = self.request.user
        if not user.is_admin:
            return queryset.filter(collector=user)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = CollectionFilterForm(self.request.GET)
        return context


class CollectionPrintView(LoginRequiredMixin, TemplateView):
    template_name = 'print_collection.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if 'id' in kwargs:
            collection_id = kwargs['id']

            collection = Collection.objects.\
                prefetch_related('collector').\
                prefetch_related('customer').\
                get(id=collection_id)

            # If the logged user is not an admin and is not the creator of the collection
            # then raise a 403 error
            user = request.user
            if not user.is_admin and user != collection.collector:
                raise PermissionDenied

            collection_installment = CollectionInstallment.objects.\
                filter(collection=collection_id).\
                prefetch_related('sale_installment').\
                prefetch_related('sale_installment__sale')
            total = CollectionInstallment.objects.\
                filter(collection=collection_id).\
                aggregate(total=Sum('amount'))

            context['collection'] = collection
            context['collection_installment'] = collection_installment
            context['total'] = total
        return self.render_to_response(context)


class LocalCollectionPrintView(LoginRequiredMixin, TemplateView):
    template_name = 'print_local_collection.html'


class CollectionDataView(LoginRequiredMixin, ContextMixin, CollectionData, View):

    def get(self, request, *args, **kwargs):
        # If the user is not an admin then filter collections by loggued user
        if request.user.is_admin:
            customers = Customer.objects.values('pk', 'name', 'address', 'telephone', 'city')
        else:
            customers = Customer.objects.filter(collector=self.request.user).values('pk', 'name', 'address', 'telephone', 'city')

        # get_data return sales and installments data
        data = self.get_data()
        data['customers'] = list(customers)
        data['last_update'] = KeyValueStore.get('sync')

        CollectorSyncLog.objects.create(user=request.user)

        return JsonResponse(data)


class PendingCollectionView(LoginRequiredMixin, TemplateView):
    template_name = 'pending_collection.html'
