from django.db.models import Min, Value, Q
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.views.generic.base import ContextMixin, TemplateResponseMixin

from app.forms import CustomUserCreationForm, CustomerCreationForm
from app.models import User, Customer, Sale, SaleInstallment


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


class SaleCreationView(CreateView):
    model = Sale
    fields = '__all__'
    template_name = 'create_sale.html'
    success_url = '/'


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