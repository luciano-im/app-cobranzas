from datetime import datetime, time

from mixer.backend.django import mixer

from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from django.forms.formsets import BaseFormSet
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone, dateformat

from app.models import User, Customer, Product, Sale, SaleInstallment, SaleProduct
from app.views import LoginView, UserCreationView, UserListView, CustomerCreationView, CustomerUpdateView, CustomerListView
from app.views import ProductCreationView, ProductUpdateView, ProductListView, SaleCreationView, SaleUpdateView
from app.views import SaleListView, FilterSetView
from app.forms import CustomAuthenticationForm, CustomUserCreationForm, CustomerCreationForm, CustomerFilterForm
from app.forms import ProductCreationForm, ProductFilterForm, SaleCreationForm, SaleWithPaymentsUpdateForm, SaleFilterForm


class RequestFactoryMixin:
    factory = RequestFactory()


class TestFilterSetView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.filterset = FilterSetView()

    def test_filterset_is_empty(self):
        self.assertEqual(self.filterset.filterset, [])

    def test_get_filters(self):
        self.filterset.filterset = [
            ('name', 'name', 'icontains'),
            ('city', 'city', 'exact'),
            ('address', 'address', 'icontains'),
        ]
        request = self.factory.get(reverse('list-customers') + '?name=Laura')
        filters = self.filterset.get_filters(request)
        self.assertEqual(filters, Q(name__icontains='Laura'))

    def test_get_filter_by_date(self):
        self.filterset.filterset = [
            ('id', 'pk', 'iexact'),
            ('customer', 'customer', 'exact'),
            ('date_from', 'date', 'gte'),
            ('date_to', 'date', 'lte'),
            ('product', 'saleproduct__product_id', 'exact'),
        ]
        request = self.factory.get(reverse('list-sales') + '?date_from=2023-01-01&date_to=2023-12-31')

        # Calculate date_from and date_to
        # Convert string date to datetime
        raw_datetime_from = datetime.strptime(request.GET['date_from'], '%Y-%m-%d')
        raw_datetime_to = datetime.strptime(request.GET['date_to'], '%Y-%m-%d')
        # Get timezone
        tz = timezone.get_current_timezone()
        # Date from: add 00:00:00 (start of the day)
        date_start = datetime.combine(raw_datetime_from, time.min)
        from_value = timezone.make_aware(date_start, tz, True)
        # Date to: add 23:59:59 hour (end of the day)
        date_end = datetime.combine(raw_datetime_to, time.max)
        to_value = timezone.make_aware(date_end, tz, True)

        filters = self.filterset.get_filters(request)
        self.assertEqual(filters, Q(date__gte=from_value, date__lte=to_value))


class TestHomeView(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)

    def test_login_required(self):
        # Intenta acceder a la vista sin autenticarse
        response = self.client.get(reverse('home'))
        # Debería redirigir a la página de inicio de sesión
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('home'))

    def test_authenticated_access(self):
        # Autenticar al usuario
        self.client.login(username='luciano', password='mypassword')
        # Intenta acceder a la vista
        response = self.client.get(reverse('home'))
        # Debería permitir el acceso si el usuario está autenticado
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        # Login a user
        self.client.login(username='luciano', password='mypassword')
        # Get the response
        response = self.client.get(reverse('home'))
        # Assert the correct template is used
        self.assertTemplateUsed(response, 'base.html')


class TestLoginView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.request = self.factory.get(reverse('login'))

    def test_status_code_200(self):
        response = LoginView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)

    def test_form_instance(self):
        view = LoginView()
        view.setup(self.request)
        context = view.get_context_data()
        self.assertIn('form', context)
        self.assertIsInstance(context['form'], CustomAuthenticationForm)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('login'))
        self.assertTemplateUsed(response, 'login.html')


class TestUserCreationView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False)
        self.request = self.factory.get(reverse('signup'))

    def test_login_required(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('signup'))

    def test_admin_required(self):
        self.client.login(username='laura', password='mypassword')
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)

    def test_status_code_200(self):
        self.request.user = self.admin
        response = UserCreationView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('signup'))
        self.assertTemplateUsed(response, 'signup_form.html')

    def test_environment_set_in_context(self):
        data = {
            'username': 'test',
            'password': 'test',
            'is_staff': False
        }
        request = self.factory.post(reverse('signup'), data)
        request.user = self.admin
        view = UserCreationView()
        view.setup(request)
        view.object = self.admin
        context = view.get_context_data()
        self.assertIn('form', context)
        self.assertIsInstance(context['form'], CustomUserCreationForm)


class TestUserListView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False)
        self.request = self.factory.get(reverse('list-users'))

    def test_login_required(self):
        response = self.client.get(reverse('list-users'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('list-users'))

    def test_admin_required(self):
        self.client.login(username='laura', password='mypassword')
        response = self.client.get(reverse('list-users'))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('list-users'))
        self.assertEqual(response.status_code, 200)

    def test_status_code_200(self):
        self.request.user = self.admin
        response = UserListView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('list-users'))
        self.assertTemplateUsed(response, 'list_users.html')

    def test_environment_set_in_context(self):
        view = UserListView()
        view.setup(self.request)
        context = view.get_context_data()
        self.assertIn('users', context)


class TestCustomerCreationView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False)
        self.request = self.factory.get(reverse('create-customer'))

    def test_login_required(self):
        response = self.client.get(reverse('create-customer'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('create-customer'))

    def test_admin_required(self):
        self.client.login(username='laura', password='mypassword')
        response = self.client.get(reverse('create-customer'))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('create-customer'))
        self.assertEqual(response.status_code, 200)

    def test_status_code_200(self):
        self.request.user = self.admin
        response = CustomerCreationView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('create-customer'))
        self.assertTemplateUsed(response, 'create_customer.html')

    def test_environment_set_in_context(self):
        data = {
            'name': 'test',
            'address': 'test'
        }
        request = self.factory.post(reverse('create-customer'), data)
        request.user = self.admin
        view = CustomerCreationView()
        view.setup(request)
        view.object = self.admin
        context = view.get_context_data()
        self.assertIn('form', context)
        self.assertIsInstance(context['form'], CustomerCreationForm)


class TestCustomerUpdateView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False)
        self.customer = mixer.blend(Customer, id=1)

    def test_login_required(self):
        response = self.client.get(reverse('update-customer', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('update-customer', kwargs={'pk': 1}))

    def test_admin_required(self):
        self.client.login(username='laura', password='mypassword')
        response = self.client.get(reverse('update-customer', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('update-customer', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)

    def test_status_code_200(self):
        request = self.factory.get(reverse('update-customer', kwargs={'pk': 1}))
        request.user = self.admin
        response = CustomerUpdateView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('update-customer', kwargs={'pk': 1}))
        self.assertTemplateUsed(response, 'update_customer.html')

    def test_get_success_url(self):
        data = {
            'name': 'Laura'
        }
        request = self.factory.post(reverse('update-customer', kwargs={'pk': 1}), data)
        view = CustomerUpdateView()
        view.setup(request)
        success_url = view.get_success_url()
        expected_url = reverse('list-customers')
        self.assertEquals(success_url, expected_url)


class TestCustomerListView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.request = self.factory.get(reverse('list-customers'))
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False)
        self.collector = User.objects.create_user(username='diego', email='test2@test2.com', password='mypassword', is_staff=False, is_collector=True)
        self.customer_1 = mixer.blend(Customer, id=1, name='Laura', collector=self.admin)
        self.customer_2 = mixer.blend(Customer, id=2, name='Andrea', collector=self.collector)

    def test_login_required(self):
        response = self.client.get(reverse('list-customers'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('list-customers'))

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('list-customers'))
        self.assertEqual(response.status_code, 200)

    def test_status_code_200(self):
        self.request.user = self.admin
        response = CustomerListView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('list-customers'))
        self.assertTemplateUsed(response, 'list_customers.html')

    def test_environment_set_in_context(self):
        self.request.user = self.admin
        view = CustomerListView()
        view.setup(self.request)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertIn('filter_form', context)
        self.assertIsInstance(context['filter_form'], CustomerFilterForm)

    def test_get_queryset_no_filters(self):
        self.request.user = self.admin
        view = CustomerListView()
        view.setup(self.request)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertEqual(len(context['object_list']), 2)
        self.assertIn(self.customer_1, context['object_list'])
        self.assertIn(self.customer_2, context['object_list'])

    def test_get_queryset_filter_by_name(self):
        request = self.factory.get(reverse('list-customers') + '?name=Laura')
        request.user = self.admin
        view = CustomerListView()
        view.setup(request)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertEqual(len(context['object_list']), 1)
        self.assertIn(self.customer_1, context['object_list'])
        self.assertNotIn(self.customer_2, context['object_list'])

    def test_get_queryset_when_user_is_not_an_admin(self):
        request = self.factory.get(reverse('list-customers') + '?name=Andrea')
        request.user = self.collector
        view = CustomerListView()
        view.setup(request)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertEqual(len(context['object_list']), 1)
        self.assertIn(self.customer_2, context['object_list'])
        self.assertNotIn(self.customer_1, context['object_list'])


class TestProductCreationView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False)
        self.request = self.factory.get(reverse('create-product'))

    def test_login_required(self):
        response = self.client.get(reverse('create-product'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('create-product'))

    def test_admin_required(self):
        self.client.login(username='laura', password='mypassword')
        response = self.client.get(reverse('create-product'))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('create-product'))
        self.assertEqual(response.status_code, 200)

    def test_status_code_200(self):
        self.request.user = self.admin
        response = ProductCreationView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('create-product'))
        self.assertTemplateUsed(response, 'create_product.html')

    def test_environment_set_in_context(self):
        data = {
            'name': 'Horno',
            'brand': 'Morelli',
            'price': 1000
        }
        request = self.factory.post(reverse('create-product'), data)
        request.user = self.admin
        view = ProductCreationView()
        view.setup(request)
        view.object = self.admin
        context = view.get_context_data()
        self.assertIn('form', context)
        self.assertIsInstance(context['form'], ProductCreationForm)


class TestProductUpdateView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False)
        self.product = mixer.blend(Product, id=1)

    def test_login_required(self):
        response = self.client.get(reverse('update-product', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('update-product', kwargs={'pk': 1}))

    def test_admin_required(self):
        self.client.login(username='laura', password='mypassword')
        response = self.client.get(reverse('update-product', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('update-product', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('update-product', kwargs={'pk': 1}))
        self.assertTemplateUsed(response, 'update_product.html')

    def test_status_code_200(self):
        request = self.factory.get(reverse('update-product', kwargs={'pk': 1}))
        request.user = self.admin
        response = ProductUpdateView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, 200)

    def test_get_success_url(self):
        data = {
            'name': 'Heladera'
        }
        request = self.factory.post(reverse('update-product', kwargs={'pk': 1}), data)
        view = ProductUpdateView()
        view.setup(request)
        success_url = view.get_success_url()
        expected_url = reverse('list-product')
        self.assertEquals(success_url, expected_url)


class TestProductListView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.request = self.factory.get(reverse('list-product'))
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False)
        self.product_1 = mixer.blend(Product, id=1, name='Heladera')
        self.product_2 = mixer.blend(Product, id=2, name='Cocina')

    def test_login_required(self):
        response = self.client.get(reverse('list-product'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('list-product'))

    def test_admin_required(self):
        self.client.login(username='laura', password='mypassword')
        response = self.client.get(reverse('list-product'))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('list-product'))
        self.assertEqual(response.status_code, 200)

    def test_status_code_200(self):
        self.request.user = self.admin
        response = ProductListView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('list-product'))
        self.assertTemplateUsed(response, 'list_products.html')

    def test_environment_set_in_context(self):
        self.request.user = self.admin
        view = ProductListView()
        view.setup(self.request)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertIn('filter_form', context)
        self.assertIsInstance(context['filter_form'], ProductFilterForm)

    def test_get_queryset_no_filters(self):
        self.request.user = self.admin
        view = ProductListView()
        view.setup(self.request)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertEqual(len(context['object_list']), 2)
        self.assertIn(self.product_1, context['object_list'])
        self.assertIn(self.product_2, context['object_list'])

    def test_get_queryset_filter_by_name(self):
        request = self.factory.get(reverse('list-product') + '?name=Heladera')
        request.user = self.admin
        view = ProductListView()
        view.setup(request)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertEqual(len(context['object_list']), 1)
        self.assertIn(self.product_1, context['object_list'])
        self.assertNotIn(self.product_2, context['object_list'])


class TestSaleCreationView(RequestFactoryMixin, TestCase):

    def setUp(self):
        self.request = self.factory.get(reverse('create-sale'))
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False, is_collector=True)
        self.customer = Customer.objects.create(
            id=1,
            name='Autoservicio Marcos',
            address='Mi Direccion 1234',
            city='ARR',
            telephone='2478505050',
            collector=self.user
        )
        self.product = mixer.blend(Product, id=1, name='Heladera')
        tz = timezone.get_current_timezone()
        self.today = timezone.make_aware(datetime.today(), tz, True)
        self.today_formatted = dateformat.format(timezone.make_aware(datetime.today(), tz, True), 'Y-m-d')

    def test_sale_creation_request_return_200(self):
        data = {
            'customer': 1,
            'collector': self.user.id,
            'saleproduct_set-TOTAL_FORMS': 1,
            'saleproduct_set-INITIAL_FORMS': 0,
            'saleproduct_set-MIN_NUM_FORMS': 0,
            'saleproduct_set-MAX_NUM_FORMS': 50,
            'saleproduct_set-0-product': self.product.id,
            'saleproduct_set-0-price': 1000,
            'price': 1000,
            'installments': 10,
            'installment_amount': 100.00,
            'sale_date': self.today_formatted
        }
        self.client.login(username='luciano', password='mypassword')
        response = self.client.post(reverse('create-sale'), data)
        # Verificar que el objeto se ha creado en la base de datos
        self.assertEqual(Sale.objects.count(), 1)
        # Verificar que la vista redirige al URL de éxito después de la creación
        self.assertRedirects(response, '/')

    def test_sale_form_invalid(self):
        data = {
            'customer': 1,
            'collector': self.user.id,
            'saleproduct_set-TOTAL_FORMS': 1,
            'saleproduct_set-INITIAL_FORMS': 0,
            'saleproduct_set-MIN_NUM_FORMS': 0,
            'saleproduct_set-MAX_NUM_FORMS': 50,
            'saleproduct_set-0-product': self.product.id,
            'saleproduct_set-0-price': 1000,
            'price': 2000,
            'installments': 10,
            'installment_amount': 200.00,
            'sale_date': self.today_formatted
        }
        self.client.login(username='luciano', password='mypassword')
        response = self.client.post(reverse('create-sale'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Sale.objects.count(), 0)

    def test_login_required(self):
        response = self.client.get(reverse('create-sale'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('create-sale'))

    def test_admin_required(self):
        self.client.login(username='laura', password='mypassword')
        response = self.client.get(reverse('create-sale'))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('create-sale'))
        self.assertEqual(response.status_code, 200)

    def test_status_code_200(self):
        self.request.user = self.admin
        response = SaleCreationView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('create-sale'))
        self.assertTemplateUsed(response, 'create_sale.html')

    def test_environment_set_in_context(self):
        self.request.user = self.admin
        view = SaleCreationView()
        view.setup(self.request)
        view.object = mixer.blend(Sale, sale_date=self.today)
        context = view.get_context_data()
        self.assertIn('form', context)
        self.assertIsInstance(context['form'], SaleCreationForm)
        self.assertIn('products', context)
        self.assertIsInstance(context['products'], BaseFormSet)


class TestSaleUpdateView(RequestFactoryMixin, TestCase):

    def setUp(self):
        tz = timezone.get_current_timezone()
        self.today = timezone.make_aware(datetime.today(), tz, True)
        self.today_formatted = dateformat.format(timezone.make_aware(datetime.today(), tz, True), 'Y-m-d')
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False, is_collector=True)
        customer = Customer.objects.create(
            id=1,
            name='Autoservicio Marcos',
            address='Mi Direccion 1234',
            city='ARR',
            telephone='2478505050',
            collector=self.user
        )
        self.sale_with_payments = mixer.blend(
            Sale,
            id=1,
            user=self.admin,
            customer=customer,
            price=1000,
            installment_amount=1000,
            installments=1,
            collector=self.user,
            uncollectible=False,
            sale_date=self.today
        )
        SaleInstallment.objects.create(
            sale=self.sale_with_payments,
            installment=1,
            installment_amount=1000,
            paid_amount=200,
            status=SaleInstallment.PARTIAL
        )
        self.sale_without_payments = mixer.blend(
            Sale,
            id=2,
            user=self.admin,
            customer=customer,
            price=3000,
            installment_amount=2000,
            installments=2,
            collector=self.user,
            uncollectible=False,
            sale_date=self.today
        )
        SaleInstallment.objects.create(
            sale=self.sale_without_payments,
            installment=1,
            installment_amount=2000,
            paid_amount=0,
            status=SaleInstallment.PENDING
        )
        self.product = mixer.blend(Product, id=1, name='Heladera')

    def test_login_required(self):
        response = self.client.get(reverse('update-sale', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('update-sale', kwargs={'pk': 1}))

    def test_admin_required(self):
        self.client.login(username='laura', password='mypassword')
        response = self.client.get(reverse('update-sale', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('update-sale', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('update-sale', kwargs={'pk': 1}))
        self.assertTemplateUsed(response, 'update_sale.html')

    def test_get_form_class_sale_with_payments(self):
        request = self.factory.get(reverse('update-sale', kwargs={'pk': 1}))
        request.user = self.admin
        view = SaleUpdateView()
        view.setup(request)
        view.object = self.sale_with_payments
        self.assertEqual(view.get_form_class(), SaleWithPaymentsUpdateForm)

    def test_get_form_class_sale_without_payments(self):
        request = self.factory.get(reverse('update-sale', kwargs={'pk': 2}))
        request.user = self.admin
        view = SaleUpdateView()
        view.setup(request)
        view.object = self.sale_without_payments
        self.assertEqual(view.get_form_class(), SaleCreationForm)

    def test_get_success_url(self):
        data = {
            'uncollectible': True
        }
        request = self.factory.post(reverse('update-sale', kwargs={'pk': 2}), data)
        view = SaleUpdateView()
        view.setup(request)
        success_url = view.get_success_url()
        expected_url = reverse('list-sales')
        self.assertEquals(success_url, expected_url)

    def test_context_installments_scheme_same_amount(self):
        request = self.factory.get(reverse('update-sale', kwargs={'pk': 1}))
        request.user = self.admin
        view = SaleUpdateView()
        view.setup(request)
        view.object = self.sale_with_payments
        context = view.get_context_data()
        self.assertIn('installments_scheme', context)
        self.assertEqual(len(context['installments_scheme']), 1)

    def test_context_installments_scheme_different_amount(self):
        request = self.factory.get(reverse('update-sale', kwargs={'pk': 2}))
        request.user = self.admin
        view = SaleUpdateView()
        view.setup(request)
        view.object = self.sale_without_payments
        context = view.get_context_data()
        self.assertIn('installments_scheme', context)
        self.assertEqual(len(context['installments_scheme']), 2)

    def test_sale_with_payments_return_validation_error_exception(self):
        incomplete_data = {
            'uncollectible': True
        }
        self.client.login(username='luciano', password='mypassword')
        with self.assertRaises(ValidationError):
            self.client.post(reverse('update-sale', kwargs={'pk': 1}), incomplete_data)

    def test_sale_without_payments_return_form_invalid(self):
        incomplete_data = {
            'uncollectible': True
        }
        self.client.login(username='luciano', password='mypassword')
        self.client.post(reverse('update-sale', kwargs={'pk': 2}), incomplete_data)
        sale = Sale.objects.get(id=self.sale_without_payments.id)
        self.assertEqual(sale.uncollectible, False)

    def test_sale_with_payments_form_valid(self):
        valid_data = {
            'customer': 1,
            'collector': self.user.id,
            'saleproduct_set-TOTAL_FORMS': 1,
            'saleproduct_set-INITIAL_FORMS': 0,
            'saleproduct_set-MIN_NUM_FORMS': 0,
            'saleproduct_set-MAX_NUM_FORMS': 50,
            'saleproduct_set-0-product': self.product.id,
            'saleproduct_set-0-price': 1000,
            'price': 1000,
            'installments': 1,
            'installment_amount': 1000,
            'uncollectible': True,
            'sale_date': self.today_formatted
        }
        self.client.login(username='luciano', password='mypassword')
        response = self.client.post(reverse('update-sale', kwargs={'pk': 1}), valid_data)
        sale = Sale.objects.get(id=self.sale_with_payments.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sale.uncollectible, True)

    def test_sale_without_payments_form_invalid(self):
        valid_data = {
            'customer': 1,
            'collector': self.user.id,
            'saleproduct_set-TOTAL_FORMS': 1,
            'saleproduct_set-INITIAL_FORMS': 0,
            'saleproduct_set-MIN_NUM_FORMS': 0,
            'saleproduct_set-MAX_NUM_FORMS': 50,
            'saleproduct_set-0-product': self.product.id,
            'saleproduct_set-0-price': 3000,
            'price': 3000,
            'installments': 2,
            'installment_amount': 2000,
            'uncollectible': True,
            'sale_date': self.today_formatted
        }
        self.client.login(username='luciano', password='mypassword')
        response = self.client.post(reverse('update-sale', kwargs={'pk': 2}), valid_data)
        sale = Sale.objects.get(id=self.sale_without_payments.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sale.uncollectible, True)


class TestSaleListView(RequestFactoryMixin, TestCase):

    def setUp(self):
        tz = timezone.get_current_timezone()
        self.today = timezone.make_aware(datetime.today(), tz, True)
        self.admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False, is_collector=True)
        customer_1 = mixer.blend(Customer, id=1, name='Autoservicio Marcos')
        customer_2 = mixer.blend(Customer, id=2, name='Jose Luis')
        self.sale_1 = Sale.objects.create(
            user=self.admin,
            customer=customer_1,
            price=1000,
            installment_amount=1000,
            installments=1,
            collector=self.user,
            sale_date=self.today
        )
        self.sale_2 = Sale.objects.create(
            user=self.admin,
            customer=customer_2,
            price=2000,
            installment_amount=2000,
            installments=1,
            collector=self.user,
            sale_date=self.today
        )
        SaleProduct.objects.create(sale=self.sale_1, product=mixer.blend(Product, id=1, name='Heladera'), price=800)
        SaleProduct.objects.create(sale=self.sale_2, product=mixer.blend(Product, id=2, name='Cocina'), price=1200)
        SaleInstallment.objects.create(sale=self.sale_1, installment=1, installment_amount=1000, paid_amount=0, status=SaleInstallment.PENDING)
        SaleInstallment.objects.create(sale=self.sale_2, installment=1, installment_amount=2000, paid_amount=1000, status=SaleInstallment.PARTIAL)

    def test_login_required(self):
        response = self.client.get(reverse('list-sales'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + reverse('list-sales'))

    def test_admin_required(self):
        self.client.login(username='laura', password='mypassword')
        response = self.client.get(reverse('list-sales'))
        self.assertEqual(response.status_code, 403)

    def test_authenticated_admin_access(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('list-sales'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username='luciano', password='mypassword')
        response = self.client.get(reverse('list-sales'))
        self.assertTemplateUsed(response, 'list_sales.html')

    def test_context_filter_form_exists(self):
        request = self.factory.get(reverse('list-sales'))
        request.user = self.admin
        view = SaleListView()
        view.setup(request)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertIn('filter_form', context)
        self.assertIsInstance(context['filter_form'], SaleFilterForm)

    def test_get_queryset_filter_by_customer(self):
        request = self.factory.get(reverse('list-sales') + '?customer=1')
        request.user = self.admin
        view = SaleListView()
        view.setup(request)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertEqual(len(context['object_list']), 1)
        self.assertIn(self.sale_1, context['object_list'])

    def test_get_queryset_filter_by_product(self):
        request = self.factory.get(reverse('list-sales') + '?product=2')
        request.user = self.admin
        view = SaleListView()
        view.setup(request)
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        self.assertEqual(len(context['object_list']), 1)
        self.assertIn(self.sale_2, context['object_list'])
