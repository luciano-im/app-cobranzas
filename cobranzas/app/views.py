from django.db import transaction
from django.db.models import Min, Value, Q, Count, Sum, F
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.views.generic.base import ContextMixin, TemplateResponseMixin

from app.forms import CustomUserCreationForm, CustomerCreationForm, SaleCreationForm
from app.forms import SaleProductFormSet, ProductCreationForm, CollectionFormset
from app.models import User, Customer, Sale, SaleInstallment, Product


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


class CustomerListView(TemplateView):
    template_name = 'list_customers.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all()
        return context


class ProductCreationView(CreateView):
    model = Product
    form_class = ProductCreationForm
    template_name = 'create_product.html'
    success_url = '/'


class ProductListView(TemplateView):
    template_name = 'list_products.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.all()
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


class SaleListView(TemplateView):
    template_name = 'list_sales.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sales'] = Sale.objects.\
            prefetch_related('saleinstallment_set').\
            annotate(products_quantity=Count('saleproduct__pk', distinct=True)).\
            annotate(paid_amount=Sum('saleinstallment__paid_amount')).\
            all()
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

        # context['salesinstallments'] = partial_installment.\
        #     union(next_installment, pending_installments).\
        #     order_by('sale', 'group', 'status', 'installment')

        initial_data = partial_installment.\
            union(next_installment, pending_installments).\
            order_by('sale', 'group', 'status', 'installment').values('installment', 'installment_amount', 'paid_amount')

        return initial_data

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        customer = request.GET.get('select-customer', None)
        if customer:
            self.initial_data = self.get_initial_data()
            context['formset'] = CollectionFormset(prefix='collection', initial=self.initial_data)

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        collection_formset = CollectionFormset(self.request.POST, initial=self.initial_data, prefix='collection')
        for f_form in collection_formset:
            if f_form.has_changed():
                print(f_form.changed_data)
        # checkboxes = request.POST.getlist('check')
        # post_data = request.POST.dict()
        # for check in checkboxes:
        #     print(check)
        #     print(post_data.get(f'payment-{check}', None))
        return self.render_to_response(context)