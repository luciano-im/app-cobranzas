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
from django.contrib.auth.views import LogoutView
from django.urls import path, include

from app.views import HomeView, UserCreationView, UserListView, CustomerCreationView, CustomerUpdateView
from app.views import CustomerListView, SaleCreationView, SaleUpdateView, SaleListView
from app.views import ProductCreationView, ProductUpdateView, ProductListView, LoginView, PendingBalanceListView
from app.views import ProductDeleteView, CustomerDeleteView, SaleDeleteView, DefaultersListView
from app.views import UncollectibleSalesListView
from collection.views import CollectionCreationView, CollectionListView, CollectionPrintView
from collection.views import CollectionDataView, PendingCollectionView, LocalCollectionPrintView
from collection.views import CollectionUpdateView, CollectionDeliveryView, CollectionDeliveryListView


urlpatterns = [
    path('silk/', include('silk.urls', namespace='silk')),
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', UserCreationView.as_view(), name='signup'),
    path('accounts/list/', UserListView.as_view(), name='list-users'),
    path('customers/create/', CustomerCreationView.as_view(), name='create-customer'),
    path('customers/update/<pk>/', CustomerUpdateView.as_view(), name='update-customer'),
    path('customers/delete/<pk>/', CustomerDeleteView.as_view(), name='delete-customer'),
    path('customers/list/', CustomerListView.as_view(), name='list-customers'),
    path('products/create/', ProductCreationView.as_view(), name='create-product'),
    path('products/update/<pk>/', ProductUpdateView.as_view(), name='update-product'),
    path('products/delete/<pk>/', ProductDeleteView.as_view(), name='delete-product'),
    path('products/list/', ProductListView.as_view(), name='list-product'),
    path('sales/create/', SaleCreationView.as_view(), name='create-sale'),
    path('sales/update/<pk>/', SaleUpdateView.as_view(), name='update-sale'),
    path('sales/delete/<pk>/', SaleDeleteView.as_view(), name='delete-sale'),
    path('sales/list/', SaleListView.as_view(), name='list-sales'),
    path('collections/create/', CollectionCreationView.as_view(), name='create-collection'),
    path('collections/update/<pk>/', CollectionUpdateView.as_view(), name='update-collection'),
    path('collections/list/', CollectionListView.as_view(), name='list-collection'),
    path('collections/delivery/', CollectionDeliveryView.as_view(), name='collection-delivery'),
    path('collections/print/<int:id>/', CollectionPrintView.as_view(), name='print-collection'),
    path('collections/print/local/', LocalCollectionPrintView.as_view(), name='print-local-collection'),
    path('collections/data/', CollectionDataView.as_view(), name='collections-data'),
    path('collections/pending/', PendingCollectionView.as_view(), name='pending-collection'),
    path('reports/collections-delivery/', CollectionDeliveryListView.as_view(), name='list-collection-delivery'),
    path('reports/pending-balance/', PendingBalanceListView.as_view(), name='list-pending-balance'),
    path('reports/defaulters/', DefaultersListView.as_view(), name='list-defaulters'),
    path('reports/uncollectible-sales', UncollectibleSalesListView.as_view(), name='list-uncollectible-sales'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    # Include SW views
    path('', include('collection.urls')),
]
