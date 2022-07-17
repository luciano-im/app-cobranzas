from django.db import transaction
from django.db.models import Min, Value, Q
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.views.generic.base import ContextMixin, TemplateResponseMixin

from app.forms import CustomUserCreationForm, CustomerCreationForm, SaleCreationForm
from app.forms import SaleProductFormSet, ProductCreationForm
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

    def form_valid(self, form):
        context = self.get_context_data()
        products = context['products']
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
        context['sales'] = Sale.objects.prefetch_related('saleinstallment_set').all()
        return context


# class CollectionCreationView(TemplateView):
class CollectionCreationView(ContextMixin, TemplateResponseMixin, View):
    template_name = 'create_collection.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all()
        context['selected_customer'] = self.request.GET.get('select-customer', None)
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        customer = request.GET.get('select-customer', None)
        if customer:
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

            context['salesinstallments'] = partial_installment.\
                union(next_installment, pending_installments).\
                order_by('sale', 'group', 'status', 'installment')

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        checkboxes = request.POST.getlist('check')
        post_data = request.POST.dict()
        for check in checkboxes:
            print(check)
            print(post_data.get(f'payment-{check}', None))
        return self.render_to_response(context)