from dateutil.relativedelta import relativedelta

from datetime import datetime, time
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Count, F, Sum, Subquery, OuterRef
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView, CreateView, ListView
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.views.generic.edit import UpdateView

from app.forms import CustomUserCreationForm, CustomerCreationForm, SaleCreationForm, SaleWithPaymentsUpdateForm
from app.forms import SaleProductCreationForm, SaleWithPaymentsProductUpdateForm, ProductCreationForm
from app.forms import CustomerFilterForm, ProductFilterForm, SaleFilterForm
from app.forms import CustomAuthenticationForm, PendingBalanceFilterForm
from app.forms import create_saleproduct_formset
from app.models import User, Customer, Sale, Product, SaleProduct, SaleInstallment

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


class ReceivableSalesView:

    def __init__(self):
        self.sales_with_pending_balance = None

    def get_customers_filter(self, customer):
        user = self.request.user
        # If user is admin get all sales
        if user.is_admin:
            if customer:
                q_filter = Q(id=customer)
            else:
                q_filter = Q()
        else:
            # If user is not an admin, and customer is not None
            if customer:
                customer_record = Customer.objects.get(id=customer)
                # If customer's collector is the current user then get all customer sales
                # If customer's collector is not the current user then get all customer sales whose collector
                # is the current user
                if customer_record.collector == user:
                    q_filter = Q(id=customer)
                else:
                    q_filter = Q(id=customer, sale__collector=user)
            else:
                # If customer is None then get sales of customers whose collector is the current user
                # and get those whose collector is the current user but the customer collector is not the current user
                q_filter = Q(collector=user) | Q(~Q(collector=user), sale__collector=user)

        return q_filter

    # TODO: Check if this method still works
    def set_sales_with_pending_balance(self, customer=None):
        filters = self.get_customers_filter(customer)
        self.sales_with_pending_balance = self.get_pending_sales(filters, ['pk', 'customer'])

    def get_pending_sales(self, filters, fields):
        return Sale.objects.\
            filter(filters, uncollectible=False).\
            annotate(paid_installments=Count('saleinstallment__pk', filter=Q(saleinstallment__status='PAID'))).\
            exclude(installments=F('paid_installments')).\
            values(*fields)

    def get_sale(self, id):
        sale = Sale.objects.get(pk=id)
        products = SaleProduct.objects.filter(sale=id).values('product__name')

        data = {
            'id': sale.pk,
            'installments': sale.installments,
            'date': sale.date.strftime('%m/%d/%Y'),
            'price': sale.price,
            'remarks': sale.remarks,
            'paid_amount': sale.paid_amount,
            'pending_balance': sale.pending_balance,
            'products': [p['product__name'] for p in products]
        }

        return data

    def get_installments(self, sale):
        installments = SaleInstallment.objects.\
            filter(sale=sale).\
            filter(Q(status=SaleInstallment.PARTIAL) | Q(status=SaleInstallment.PENDING)).\
            order_by('sale', 'installment', 'status').\
            values('pk', 'sale_id', 'status', 'installment', 'installment_amount', 'paid_amount')

        return installments


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'


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


class CustomerUpdateView(LoginRequiredMixin, AdminPermission, UpdateView):
    model = Customer
    form_class = CustomerCreationForm
    template_name = 'update_customer.html'

    def get_success_url(self):
        return reverse('list-customers')


class CustomerListView(LoginRequiredMixin, ListView, FilterSetView):
    template_name = 'list_customers.html'
    context_object_name = 'customers'
    filterset = []

    def get_queryset(self):
        # If the user is an admin then enable filter by collector
        user = self.request.user
        self.filterset = [
            ('name', 'name', 'icontains'),
            ('city', 'city', 'exact'),
            ('address', 'address', 'icontains'),
        ]
        if user.is_admin:
            self.filterset.append(('collector', 'collector', 'exact'))

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


class ProductUpdateView(LoginRequiredMixin, AdminPermission, UpdateView):
    model = Product
    form_class = ProductCreationForm
    template_name = 'update_product.html'

    def get_success_url(self):
        return reverse('list-product')


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
            context['products'] = create_saleproduct_formset(1, form=SaleProductCreationForm, data=self.request.POST)
        else:
            context['products'] = create_saleproduct_formset(1, form=SaleProductCreationForm)
        return context

    @silk_profile(name='SaleCreation post')
    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        product_formset = create_saleproduct_formset(1, form=SaleProductCreationForm, data=self.request.POST)
        if form.is_valid() and product_formset.is_valid():
            # Check if the sum of each product price is equal to the price of the sale
            total_price = 0.0
            for formset in product_formset:
                total_price += formset.cleaned_data.get('price', 0.0)
            if form.cleaned_data.get('price') == total_price:
                return self.form_valid(form, product_formset)

        return self.form_invalid(form)

    def form_valid(self, form, formset):
        # Add the user to the form
        form.instance.user = self.request.user
        products = formset
        with transaction.atomic():
            self.object = form.save()
            if products.is_valid():
                products.instance = self.object
                products.save()
        return super().form_valid(form)


class SaleUpdateView(LoginRequiredMixin, AdminPermission, UpdateView):
    model = Sale
    template_name = 'update_sale.html'
    add_product_button_disabled = False
    add_product_formset = SaleProductCreationForm

    def get_form_class(self):
        if self.object.paid_amount > 0:
            self.add_product_button_disabled = True
            self.add_product_formset = SaleWithPaymentsProductUpdateForm
            return SaleWithPaymentsUpdateForm
        return SaleCreationForm

    def get_success_url(self):
        return reverse('list-sales')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = create_saleproduct_formset(0, form=self.add_product_formset, data=self.request.POST or None, files=self.request.FILES or None, instance=self.object)
        context['add_product_button_disabled'] = self.add_product_button_disabled

        calculated_price = self.object.installment_amount * self.object.installments
        price = self.object.price
        if calculated_price == price:
            context['installments_scheme'] = [
                {
                    'installments': self.object.installments,
                    'installment_amount': self.object.installment_amount
                }
            ]
        else:
            context['installments_scheme'] = [
                {
                    'installments': self.object.installments - 1,
                    'installment_amount': self.object.installment_amount
                },
                {
                    'installments': 1,
                    'installment_amount': round(price - ((self.object.installments - 1) * self.object.installment_amount), 2)
                }
            ]
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        product_formset = create_saleproduct_formset(0, form=self.add_product_formset, data=self.request.POST, instance=self.object)

        # If sale has already paid installments
        if self.object.paid_amount > 0:
            # If formset is valid then update each product
            if product_formset.is_valid():
                return self.form_valid(form, product_formset)
            else:
                return ValidationError(product_formset.errors)
        else:
            # If form and product formset are valid, calculate total price and continue with form_valid
            if form.is_valid() and product_formset.is_valid():
                return self.form_valid(form, product_formset)

            return self.form_invalid(form)

    def form_valid(self, form, formset):
        # Add the user to the form
        form.instance.user = self.request.user
        products = formset
        with transaction.atomic():
            self.object = form.save()
            if products.is_valid():
                products.sale = self.object
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

    @silk_profile(name='SaleList get_queryset')
    def get_queryset(self):
        filters = self.get_filters(self.request)
        if filters:
            queryset = Sale.objects.\
                filter(filters).\
                prefetch_related('saleinstallment_set').\
                annotate(products_quantity=Count('saleproduct__pk', distinct=True)).\
                all()
        else:
            # Filter last month by default
            queryset = Sale.objects.\
                filter(date__gte=timezone.now() - relativedelta(days=7)).\
                prefetch_related('saleinstallment_set').\
                annotate(products_quantity=Count('saleproduct__pk', distinct=True)).\
                all()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = SaleFilterForm(self.request.GET)
        return context


class UncollectibleSaleCreateView(LoginRequiredMixin, AdminPermission, ContextMixin, TemplateResponseMixin, ReceivableSalesView, View):
    template_name = 'create_uncollectible.html'

    def get_uncollectible_data(self, customer):
        self.set_sales_with_pending_balance(customer)
        data = []

        for s in self.sales_with_pending_balance:
            installments = self.get_installments(s['pk'])
            temp = self.get_sale(s['pk'])
            temp['installments_data'] = installments

            data.append(temp)

        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.collector = self.request.user
        context['customers'] = Customer.objects.values('pk', 'name').order_by('name')
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        selected_customer_param = self.request.GET.get('select-customer', None)
        selected_customer = int(selected_customer_param) if selected_customer_param is not None else selected_customer_param

        if selected_customer:
            # get_data return sales and installments data
            data = self.get_uncollectible_data(selected_customer)
            # data['customers'] = list(context['customers'])
            # data['selected_customer'] = selected_customer
            context['selected_customer'] = selected_customer
            context['data'] = data

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        selected_customer = request.POST.get('customer', None)
        customer = Customer.objects.get(id=selected_customer)
        if customer:
            checkboxes = request.POST.getlist('uncollectible-sale', None)
            if checkboxes:
                for sale in checkboxes:
                    try:
                        Sale.objects.filter(customer=customer, id=sale).update(uncollectible=True)
                    except:
                        raise ValidationError(_('Error when setting uncollectible status to a sale'))
        else:
            raise PermissionDenied

        return self.render_to_response(context)


class PendingBalanceListView(LoginRequiredMixin, AdminPermission, ListView, FilterSetView, ReceivableSalesView):
    template_name = 'list_pending_balance.html'
    context_object_name = 'pending_balance'
    filterset = [
        ('customer', 'customer', 'exact'),
        ('city', 'customer__city', 'exact')
    ]

    def get_queryset(self):
        filters = self.get_filters(self.request)
        sales_with_pending_balance = Sale.objects.\
            filter(filters).\
            filter(uncollectible=False).\
            annotate(paid_installments=Count('saleinstallment__pk', filter=Q(saleinstallment__status='PAID'))).\
            exclude(installments=F('paid_installments'))
        # OuterRef makes reference to a field from the parent subquuery
        # OuterReg can be used only in a Subquery
        paid_amount_sum = SaleInstallment.objects.filter(sale=OuterRef('pk')).values('sale').annotate(paid_amount_sum=Sum('paid_amount')).values('paid_amount_sum')
        queryset = Sale.objects.\
            filter(pk__in=Subquery(sales_with_pending_balance.values('pk'))).\
            values('customer__id', 'customer__name', 'customer__city').\
            annotate(price=Sum('price'), paid_amount=Sum(Subquery(paid_amount_sum))).\
            annotate(pending_balance=F('price') - F('paid_amount')).\
            order_by('-pending_balance')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context['filter_form'] = PendingBalanceFilterForm(self.request.GET)
        context['total'] = queryset.aggregate(total=Sum('pending_balance'))
        return context