from django.shortcuts import render
from django.views.generic import TemplateView, CreateView

from app.forms import CustomUserCreationForm
from app.models import User


class HomeView(TemplateView):
    template_name = 'base.html'


class UserCreationView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'signup_form.html'
    success_url = '/'