from dateutil.relativedelta import relativedelta

from datetime import datetime, time
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Count, F, Sum, Subquery, OuterRef, Max
from django.db.models import Case, Value, When
from django.db.models.functions import Coalesce, ExtractDay
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView, CreateView, ListView, DeleteView
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.views.generic.edit import UpdateView

from app.forms import CustomUserCreationForm, CustomerCreationForm, SaleCreationForm, SaleWithPaymentsUpdateForm
from app.forms import SaleProductCreationForm, SaleWithPaymentsProductUpdateForm, ProductCreationForm
from app.forms import CustomerFilterForm, ProductFilterForm, SaleFilterForm
from app.forms import CustomAuthenticationForm, PendingBalanceFilterForm, UncollectibleSalesFilterForm
from app.forms import create_saleproduct_formset
from app.models import User, Customer, Sale, Product, SaleProduct, SaleInstallment
from collection.models import CollectionInstallment

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

    def get_pending_sales(self, filters, fields):
        return Sale.objects.\
            filter(filters, uncollectible=False).\
            annotate(paid_installments=Count('saleinstallment__pk', filter=Q(saleinstallment__status='PAID'))).\
            exclude(installments__lte=F('paid_installments')).\
            values(*fields)


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


class CustomerDeleteView(LoginRequiredMixin, AdminPermission, DeleteView):
    model = Customer
    success_url = reverse_lazy('list-customers')

    def form_valid(self, form):
        self.object = self.get_object()
        if not Sale.objects.filter(customer=self.object).exists():
            success_url = self.get_success_url()
            self.object.delete()
            return HttpResponseRedirect(success_url)
        else:
            messages.add_message(self.request, messages.ERROR, _("There are sales made to this customer, it cannot be deleted!"))
            return HttpResponseRedirect(reverse('update-customer', kwargs={"pk": self.object.pk}))


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
            queryset = Customer.objects.select_related('collector').filter(filters)
        else:
            queryset = Customer.objects.select_related('collector').all()

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


class ProductDeleteView(LoginRequiredMixin, AdminPermission, DeleteView):
    model = Product
    success_url = reverse_lazy('list-product')

    def form_valid(self, form):
        self.object = self.get_object()
        if not SaleProduct.objects.filter(product=self.object).exists():
            success_url = self.get_success_url()
            self.object.delete()
            return HttpResponseRedirect(success_url)
        else:
            messages.add_message(self.request, messages.ERROR, _("The product has already been used in a sale, it cannot be deleted!"))
            return HttpResponseRedirect(reverse('update-product', kwargs={"pk": self.object.pk}))


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
                raise ValidationError(product_formset.errors)
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


class SaleDeleteView(LoginRequiredMixin, AdminPermission, DeleteView):
    model = Sale
    success_url = reverse_lazy('list-sales')

    def form_valid(self, form):
        self.object = self.get_object()
        if not SaleInstallment.objects.filter(sale=self.object, paid_amount__gt=0.0).exists():
            success_url = self.get_success_url()
            self.object.delete()
            return HttpResponseRedirect(success_url)
        else:
            messages.add_message(self.request, messages.ERROR, _("This sale has already paid installments, it cannot be deleted!"))
            return HttpResponseRedirect(reverse('update-sale', kwargs={"pk": self.object.pk}))


class SaleListView(LoginRequiredMixin, AdminPermission, ListView, FilterSetView):
    template_name = 'list_sales.html'
    context_object_name = 'sales'
    filterset = [
        ('id', 'pk', 'iexact'),
        ('customer', 'customer', 'exact'),
        ('date_from', 'sale_date', 'gte'),
        ('date_to', 'sale_date', 'lte'),
        ('product', 'saleproduct__product_id', 'exact'),
    ]

    @silk_profile(name='SaleList get_queryset')
    def get_queryset(self):
        filters = self.get_filters(self.request)
        if filters:
            queryset = Sale.objects.\
                filter(filters).\
                prefetch_related('saleinstallment_set', 'saleproduct_set').\
                select_related('customer').\
                annotate(products_quantity=Count('saleproduct__pk', distinct=True))
        else:
            # Filter last month by default
            queryset = Sale.objects.\
                filter(sale_date__gte=timezone.now() - relativedelta(days=7)).\
                prefetch_related('saleinstallment_set', 'saleproduct_set').\
                select_related('customer').\
                annotate(products_quantity=Count('saleproduct__pk', distinct=True))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context['filter_form'] = SaleFilterForm(self.request.GET)

        # Get paid (totally or partially) installments ID
        sale_installments = SaleInstallment.objects.\
            filter(sale_id__in=Subquery(queryset.values('pk'))).\
            filter(~Q(status='PENDING'))
        # Calculate last payment date for paid installments
        last_payment_list = CollectionInstallment.objects.\
            filter(sale_installment__in=sale_installments.values('pk')).\
            annotate(last_payment=Max('collection__date')).\
            values('sale_installment', 'last_payment')
        # Pass installment/payment_date to context as a dictionary
        context['last_payment_list'] = {e['sale_installment']: e['last_payment'] for e in last_payment_list}

        return context


class PendingBalanceListView(LoginRequiredMixin, AdminPermission, ListView, FilterSetView, ReceivableSalesView):
    template_name = 'list_pending_balance.html'
    context_object_name = 'pending_balance'
    filterset = [
        ('customer', 'customer', 'exact'),
        ('city', 'customer__city', 'exact')
    ]

    def get_queryset(self):
        filters = self.get_filters(self.request)

        collector = self.request.GET.get('collector', None)
        if collector:
            filters = filters & (Q(customer__collector=collector) | Q(collector=collector))

        sales_with_pending_balance = Sale.objects.\
            filter(filters).\
            filter(uncollectible=False).\
            annotate(paid_installments=Count('saleinstallment__pk', filter=Q(saleinstallment__status='PAID'))).\
            exclude(installments__lte=F('paid_installments'))
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


class DefaultersListView(LoginRequiredMixin, AdminPermission, ListView, FilterSetView, ReceivableSalesView):
    template_name = 'list_defaulters.html'
    context_object_name = 'defaulters'
    filterset = [
        ('customer', 'customer', 'exact'),
        ('city', 'customer__city', 'exact')
    ]

    def get_queryset(self):
        filters = self.get_filters(self.request)
        tz = timezone.get_current_timezone()
        today_date = timezone.make_aware(datetime.today(), tz, True)

        queryset = Sale.objects.\
            filter(filters).\
            filter(uncollectible=False).\
            values('customer__id', 'customer__name', 'customer__city', 'id', 'sale_date', 'remarks').\
            annotate(paid_installments=Count('saleinstallment__pk', filter=Q(saleinstallment__status='PAID'))).\
            annotate(pending_installments=Count('saleinstallment__pk', filter=~Q(saleinstallment__status='PAID'))).\
            exclude(installments__lte=F('paid_installments')).\
            annotate(last_payment_date=Max('saleinstallment__collectioninstallment__collection__date')).\
            annotate(debt_days=ExtractDay(today_date - Coalesce(F('last_payment_date'), F('sale_date')))).\
            annotate(qualification=Case(
                When(debt_days__lte=7, then=Value(0)),
                When(debt_days__lte=15, then=Value(7)),
                When(debt_days__lte=30, then=Value(15)),
                default=Value(30)
            )).\
            exclude(qualification=0).\
            order_by('-qualification', 'customer__name', '-debt_days')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = PendingBalanceFilterForm(self.request.GET)
        return context


class UncollectibleSalesListView(LoginRequiredMixin, AdminPermission, ListView, FilterSetView):
    template_name = 'list_uncollectible_sales.html'
    context_object_name = 'sales'
    filterset = [
        ('customer', 'customer', 'exact'),
        ('date_from', 'date', 'gte'),
        ('date_to', 'date', 'lte'),
    ]

    def get_queryset(self):
        filters = self.get_filters(self.request)
        if filters:
            queryset = Sale.objects.\
                filter(filters).\
                filter(uncollectible=True).\
                prefetch_related('saleinstallment_set', 'saleproduct_set', 'customer').\
                annotate(pending_installments=Count('saleinstallment__pk', filter=~Q(saleinstallment__status='PAID')))
        else:
            # Filter last month by default
            queryset = Sale.objects.\
                filter(sale_date__gte=timezone.now() - relativedelta(months=1)).\
                filter(uncollectible=True).\
                prefetch_related('saleinstallment_set', 'saleproduct_set', 'customer').\
                annotate(pending_installments=Count('saleinstallment__pk', filter=~Q(saleinstallment__status='PAID')))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = UncollectibleSalesFilterForm(self.request.GET)
        return context