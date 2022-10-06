from datetime import datetime, time
from django.utils import timezone
from collections import defaultdict
from django.db import transaction
from django.db.models import Min, Value, Q, Count, Sum, F
from django.views import View
from django.views.generic import TemplateView, CreateView, ListView
from django.views.generic.base import ContextMixin, TemplateResponseMixin

from app.forms import CustomUserCreationForm, CustomerCreationForm, SaleCreationForm
from app.forms import SaleProductFormSet, ProductCreationForm, CollectionFormset
from app.forms import CustomerFilterForm, ProductFilterForm, SaleFilterForm
from app.models import User, Customer, Sale, SaleInstallment, Product, Collection


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


class HomeView(TemplateView):
    template_name = 'base.html'


class UserCreationView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'signup_form.html'
    success_url = '/'


class UserListView(TemplateView):
    template_name = 'list_users.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all()
        return context


class CustomerCreationView(CreateView):
    model = Customer
    form_class = CustomerCreationForm
    template_name = 'create_customer.html'
    success_url = '/'


class CustomerListView(ListView, FilterSetView):
    template_name = 'list_customers.html'
    context_object_name = 'customers'
    filterset = [
        ('city', 'city', 'exact'),
        ('collector', 'collector', 'exact'),
    ]

    def get_queryset(self):
        filters = self.get_filters(self.request)
        if filters:
            queryset = Customer.objects.filter(filters)
        else:
            queryset = Customer.objects.all()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = CustomerFilterForm(self.request.GET)
        return context


class ProductCreationView(CreateView):
    model = Product
    form_class = ProductCreationForm
    template_name = 'create_product.html'
    success_url = '/'


class ProductListView(ListView, FilterSetView):
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


class SaleCreationView(CreateView):
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

    # def get_success_url(self):
    #     return reverse_lazy('mycollections:collection_detail', kwargs={'pk': self.object.pk})


class SaleListView(ListView, FilterSetView):
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
                annotate(paid_amount=Sum('saleinstallment__paid_amount')).\
                all()
        else:
            queryset = Sale.objects.\
                prefetch_related('saleinstallment_set').\
                annotate(products_quantity=Count('saleproduct__pk', distinct=True)).\
                annotate(paid_amount=Sum('saleinstallment__paid_amount')).\
                all()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = SaleFilterForm(self.request.GET)
        return context


# class CollectionCreationView(TemplateView):
class CollectionCreationView(ContextMixin, TemplateResponseMixin, View):
    template_name = 'create_collection.html'
    initial_data = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all()
        context['selected_customer'] = self.request.GET.get('select-customer', None)
        return context

    def get_initial_data(self, ):
        partial_installment = SaleInstallment.objects.\
            filter(status='PARTIAL').\
            select_related('sale').\
            annotate(group=Value('due'))
        filter = SaleInstallment.objects.\
            filter(status='PENDING').\
            values('sale').\
            annotate(next_installment=Min('installment'))
        q_filter = Q()
        for pair in filter:
            q_filter |= (Q(sale=pair['sale']) & Q(installment=pair['next_installment']))
        next_installment = SaleInstallment.objects.\
            filter(q_filter).\
            select_related('sale').\
            annotate(group=Value('due'))
        pending_installments = SaleInstallment.objects.\
            filter(status='PENDING').\
            exclude(q_filter).\
            select_related('sale').\
            annotate(group=Value('future'))

        initial_data = partial_installment.\
            union(next_installment, pending_installments).\
            order_by('sale', 'group', 'status', 'installment').\
            values()

        return initial_data

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        customer = request.GET.get('select-customer', None)
        if customer:
            self.initial_data = self.get_initial_data()
            context['formset'] = CollectionFormset(prefix='collection', initial=self.initial_data)
            sales = Sale.objects.\
                annotate(paid_installments=Count('saleinstallment__pk', filter=Q(saleinstallment__status='PAID'))).\
                annotate(total_paid=Sum('saleinstallment__paid_amount')).\
                exclude(installments=F('paid_installments'))
            products_raw = sales.values('pk', 'saleproduct__product__name')
            products = defaultdict()
            for p in products_raw:
                products.setdefault(p['pk'], []).append(p['saleproduct__product__name'])

            context['sales'] = dict((s.pk, s) for s in sales)
            context['products'] = products
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        collection_formset = CollectionFormset(self.request.POST, initial=self.initial_data, prefix='collection')
        for f_form in collection_formset:
            if f_form.has_changed():
                if 'checked' and 'amount' in f_form.changed_data:
                    if f_form.is_valid():
                        data = f_form.cleaned_data
                        sale_installment = SaleInstallment.objects.get(sale=data['sale_id'], installment=data['installment'])
                        # TODO - Use request.user
                        user = User.objects.get(username='andrea')
                        collection = Collection(
                            collector=user,
                            sale_installment=sale_installment,
                            amount=data['amount']
                        )

                        installment_amount = sale_installment.installment_amount
                        paid_amount = sale_installment.paid_amount
                        if installment_amount > paid_amount + data['amount']:
                            sale_installment.status = SaleInstallment.PARTIAL
                        else:
                            sale_installment.status = SaleInstallment.PAID
                        sale_installment.paid_amount = F('paid_amount') + data['amount']

                        with transaction.atomic():
                            collection.save()
                            sale_installment.save()
                    else:
                        print(f_form.errors)
        return self.render_to_response(context)