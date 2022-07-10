"""cobranzas URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from app.views import HomeView, UserCreationView, UserListView, CustomerCreationView, CustomerListView, SaleCreationView, SaleListView, CollectionCreationView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', UserCreationView.as_view(), name='signup'),
    path('accounts/list/', UserListView.as_view(), name='list-users'),
    path('customers/create/', CustomerCreationView.as_view(), name='create-customer'),
    path('customers/list/', CustomerListView.as_view(), name='list-customers'),
    path('sales/create/', SaleCreationView.as_view(), name='create-sale'),
    path('sales/list/', SaleListView.as_view(), name='list-sales'),
    path('collections/create/', CollectionCreationView.as_view(), name='create-collection')
]
