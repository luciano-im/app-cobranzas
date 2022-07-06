from django.shortcuts import render
from django.views.generic import TemplateView, CreateView

from app.forms import CustomUserCreationForm, CustomerCreationForm
from app.models import User, Customer, Sale


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
        context['sales'] = Sale.objects.all()
        return context