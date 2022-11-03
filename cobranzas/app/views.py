from datetime import datetime, time
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Min, Value, Q, Count, Sum, F
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, CreateView, ListView
from django.views.generic.base import ContextMixin, TemplateResponseMixin

from app.forms import CustomUserCreationForm, CustomerCreationForm, SaleCreationForm
from app.forms import SaleProductFormSet, ProductCreationForm, CollectionFormset
from app.forms import CustomerFilterForm, ProductFilterForm, SaleFilterForm, CollectionFilterForm
from app.forms import CustomAuthenticationForm
from app.models import User, Customer, Sale, SaleProduct, SaleInstallment, Product, Collection
from app.models import CollectionInstallment

from app.permissions import AdminPermission

from silk.profiling.profiler import silk_profile


class FilterSetView:

    def __init__(self):
        # Filter set is a list of tuples containing (url_param, field, lookup_expression)
        self.filterset = []

    def get_filters(self, request):
        q_lookup = Q()
        filterset = self.filterset
        for filter in filterset:
            param, field, expr = filter[0], filter[1], filter[2]
            value = request.GET.get(param, None)
            # Make dates aware
            if 'date' in field and value:
                # Convert string date to datetime
                raw_datetime = datetime.strptime(value, '%Y-%m-%d')
                # Get timezone
                tz = timezone.get_current_timezone()
                if 'date_to' in param:
                    # If param is date_to then add 23:59:59 hour (end of the day)
                    date_end = datetime.combine(raw_datetime, time.max)
                    value = timezone.make_aware(date_end, tz, True)
                else:
                    # Else add 00:00:00 (start of the day)
                    date_start = datetime.combine(raw_datetime, time.min)
                    value = timezone.make_aware(date_start, tz, True)
            if value:
                q_lookup = q_lookup & Q(**{f'{field}__{expr}': value})
        return q_lookup


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'base.html'


class LoginView(LoginView):
    template_name = 'login.html'
    authentication_form = CustomAuthenticationForm


class UserCreationView(LoginRequiredMixin, AdminPermission, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'signup_form.html'
    success_url = '/'


class UserListView(LoginRequiredMixin, AdminPermission, TemplateView):
    template_name = 'list_users.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all()
        return context


class CustomerCreationView(LoginRequiredMixin, AdminPermission, CreateView):
    model = Customer
    form_class = CustomerCreationForm
    template_name = 'create_customer.html'
    success_url = '/'


class CustomerListView(LoginRequiredMixin, ListView, FilterSetView):
    template_name = 'list_customers.html'
    context_object_name = 'customers'
    filterset = []

    def get_queryset(self):
        # If the user is an admin then enable filter by collector
        user = self.request.user
        if user.is_admin:
            self.filterset = [
                ('city', 'city', 'exact'),
                ('collector', 'collector', 'exact'),
            ]
        else:
            self.filterset = [
                ('city', 'city', 'exact'),
            ]

        filters = self.get_filters(self.request)
        if filters:
            queryset = Customer.objects.filter(filters)
        else:
            queryset = Customer.objects.all()

        # If the user is not an admin then filter customers assigned to the loggued user
        if not user.is_admin:
            return queryset.filter(collector=user)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = CustomerFilterForm(self.request.GET)
        return context


class ProductCreationView(LoginRequiredMixin, AdminPermission, CreateView):
    model = Product
    form_class = ProductCreationForm
    template_name = 'create_product.html'
    success_url = '/'


class ProductListView(LoginRequiredMixin, AdminPermission, ListView, FilterSetView):
    template_name = 'list_products.html'
    context_object_name = 'products'
    filterset = [
        ('name', 'name', 'icontains'),
        ('brand', 'brand', 'iexact'),
        ('sku', 'sku', 'icontains'),
    ]

    def get_queryset(self):
        filters = self.get_filters(self.request)
        if filters:
            queryset = Product.objects.filter(filters)
        else:
            queryset = Product.objects.all()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ProductFilterForm(self.request.GET)
        return context


class SaleCreationView(LoginRequiredMixin, AdminPermission, CreateView):
    model = Sale
    template_name = 'create_sale.html'
    form_class = SaleCreationForm
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['products'] = SaleProductFormSet(self.request.POST)
        else:
            context['products'] = SaleProductFormSet()
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        product_formset = SaleProductFormSet(self.request.POST)
        if form.is_valid() and product_formset.is_valid():
            # Check if the sum of each product price is equal to the price of the sale
            total_price = 0.0
            for formset in product_formset:
                total_price += formset.cleaned_data.get('price', 0.0)
            if form.cleaned_data.get('price') == total_price:
                return self.form_valid(form, product_formset)

        return self.form_invalid(form)

    def form_valid(self, form, formset):
        products = formset
        with transaction.atomic():
            self.object = form.save()
            if products.is_valid():
                products.instance = self.object
                products.save()
        return super().form_valid(form)


class SaleListView(LoginRequiredMixin, AdminPermission, ListView, FilterSetView):
    template_name = 'list_sales.html'
    context_object_name = 'sales'
    filterset = [
        ('id', 'pk', 'iexact'),
        ('customer', 'customer', 'exact'),
        ('date_from', 'date', 'gte'),
        ('date_to', 'date', 'lte'),
        ('product', 'saleproduct__product_id', 'exact'),
    ]

    def get_queryset(self):
        filters = self.get_filters(self.request)
        if filters:
            queryset = Sale.objects.\
                filter(filters).\
                prefetch_related('saleinstallment_set').\
                annotate(products_quantity=Count('saleproduct__pk', distinct=True)).\
                all()
        else:
            queryset = Sale.objects.\
                prefetch_related('saleinstallment_set').\
                annotate(products_quantity=Count('saleproduct__pk', distinct=True)).\
                all()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = SaleFilterForm(self.request.GET)
        return context


# TODO: If user is not an admin then query just for the customers assigned to the user
# TODO: Improve template performance when loading lots of formset
class CollectionCreationView(LoginRequiredMixin, ContextMixin, TemplateResponseMixin, View):
    template_name = 'create_collection.html'

    def get_initial_data(self, customer):
        data = dict()
        sales_with_pending_balance = self.get_sales_with_pending_balance(customer)

        for s in sales_with_pending_balance:
            partial_installment = SaleInstallment.objects.\
                filter(status='PARTIAL', sale=s['pk']).\
                annotate(group=Value('due')).\
                order_by('sale', 'group', 'status', 'installment').\
                values('pk', 'group', 'status', 'installment', 'installment_amount', 'paid_amount')

            filter = SaleInstallment.objects.\
                filter(status='PENDING', sale=s['pk']).\
                values('sale').\
                annotate(next_installment=Min('installment'))
            q_filter = Q()
            for pair in filter:
                q_filter |= (Q(sale=pair['sale']) & Q(installment=pair['next_installment']))
            next_installment = SaleInstallment.objects.\
                filter(q_filter, sale=s['pk']).\
                annotate(group=Value('due')).\
                order_by('sale', 'group', 'status', 'installment').\
                values()

            pending_installments = SaleInstallment.objects.\
                filter(status='PENDING', sale=s['pk']).\
                exclude(q_filter).\
                annotate(group=Value('future')).\
                order_by('sale', 'group', 'status', 'installment').\
                values()

            data[s['pk']] = {
                'partial': list(partial_installment),
                'next': list(next_installment),
                'pending': list(pending_installments)
            }
        return data

    def get_sales_with_pending_balance(self, customer):
        return Sale.objects.\
            filter(customer=customer).\
            annotate(paid_installments=Count('saleinstallment__pk', filter=Q(saleinstallment__status='PAID'))).\
            exclude(installments=F('paid_installments')).\
            values('pk')

    def get_sales_detail(self, customer):
        data = dict()
        sales_with_pending_balance = self.get_sales_with_pending_balance(customer)
        for s in sales_with_pending_balance:
            sale = Sale.objects.get(pk=s['pk'])
            products = SaleProduct.objects.filter(sale=s['pk']).values('product__name')
            data[s['pk']] = {
                'id': sale.pk,
                'installments': sale.installments,
                'date': sale.date,
                'price': sale.price,
                'paid_amount': sale.paid_amount,
                'pending_balance': sale.pending_balance,
                'products': [p['product__name'] for p in products]
            }
        return data

    @silk_profile(name='Collection Get')
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['customers'] = Customer.objects.values('pk', 'name')
        selected_customer_param = self.request.GET.get('select-customer', None)
        selected_customer = int(selected_customer_param) if selected_customer_param is not None else selected_customer_param
        context['selected_customer'] = selected_customer
        if selected_customer:
            sales_data = self.get_sales_detail(selected_customer)
            installments_data = self.get_initial_data(selected_customer)
            obj = {
                'sales': sales_data,
                'customers': list(context['customers']),
                'selected_customer': selected_customer,
                'installments': installments_data
            }
            return JsonResponse(obj)
        else:
            return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        selected_customer = request.POST.get('customer', None)
        customer = Customer.objects.get(id=selected_customer)
        if customer:
            collection_formset = CollectionFormset(
                self.request.POST,
                initial=self.initial_data,
                prefix='collection'
            )
            # If there is an exception commits are rolled back
            with transaction.atomic():
                collection = None

                for f_form in collection_formset:
                    # If form doesn't change then it remains unpaid
                    if f_form.has_changed():
                        # If form has changed the fields "checked" and "amount" then it is being paid
                        # an installment
                        if 'checked' and 'amount' in f_form.changed_data:
                            # Check if form is valid or not
                            if f_form.is_valid():
                                data = f_form.cleaned_data

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
        return self.render_to_response(context)


class CollectionListView(LoginRequiredMixin, ListView, FilterSetView):
    template_name = 'list_collection.html'
    context_object_name = 'collections'
    filterset = [
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
