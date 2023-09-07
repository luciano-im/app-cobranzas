from datetime import datetime, time
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Count
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, CreateView, ListView
from django.views.generic.edit import UpdateView

from app.forms import CustomUserCreationForm, CustomerCreationForm, SaleCreationForm, SaleWithPaymentsUpdateForm
from app.forms import SaleProductCreationForm, SaleWithPaymentsProductUpdateForm, ProductCreationForm
from app.forms import CustomerFilterForm, ProductFilterForm, SaleFilterForm
from app.forms import CustomAuthenticationForm
from app.forms import create_saleproduct_formset
from app.models import User, Customer, Sale, Product, SaleProduct

from app.permissions import AdminPermission


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
        if(calculated_price == price):
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
                # Check if the sum of each product price is equal to the price of the sale
                total_price = 0.0
                for formset in product_formset:
                    total_price += formset.cleaned_data.get('price', 0.0)
                if form.cleaned_data.get('price') == total_price:
                    return self.form_valid(form, product_formset)

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
