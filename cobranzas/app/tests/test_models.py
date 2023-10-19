import datetime
import time

from mixer.backend.django import mixer

from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from app.models import User, Customer, Product, Sale, SaleInstallment, SaleProduct
from app.models import SaleInstallment, LoginLog, KeyValueStore
from app.signals import preSave_Sale, postSave_Sale, update_sync_value


class UserModelTest(TestCase):

    def setUp(self):
        self.user_admin = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_staff=True)
        self.user = User.objects.create_user(username='laura', email='test2@test.com', password='mypassword', is_staff=False)

    def test_user_instance(self):
        self.assertTrue(isinstance(self.user_admin, User))
        self.assertTrue(isinstance(self.user, User))

    def test_user_is_admin(self):
        self.assertTrue(self.user_admin.is_admin)
        self.assertFalse(self.user.is_admin)


class CustomerModelTest(TestCase):

    def setUp(self):
        # Disconnect Signals
        post_save.disconnect(receiver=update_sync_value, sender=Customer, dispatch_uid='app.signals.update_sync_value.Customer')

        collector = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_collector=True)
        self.customer = Customer.objects.create(
            name='Autoservicio Marcos',
            address='Mi Direccion 1234',
            city='ARR',
            telephone='2478505050',
            collector=collector
        )

    def test_customer_instance(self):
        self.assertTrue(isinstance(self.customer, Customer))

    def test_customer_str(self):
        self.assertEqual(str(self.customer), 'Autoservicio Marcos')


class ProductModelTest(TestCase):

    def setUp(self):
        self.product = Product.objects.create(
            id=1,
            name='Cocina',
            brand='Morelli',
            price=1.00,
            sku='M101'
        )

    def test_product_instance(self):
        self.assertTrue(isinstance(self.product, Product))

    def test_product_str(self):
        self.assertEqual(str(self.product), '1 - Cocina Morelli')


class SaleModelTest(TestCase):

    def setUp(self):
        # Disconnect Signals
        pre_save.disconnect(receiver=preSave_Sale, sender=Sale, dispatch_uid='app.signals.preSave_Sale')
        post_save.disconnect(receiver=postSave_Sale, sender=Sale, dispatch_uid='app.signals.postSave_Sale')
        post_save.disconnect(receiver=update_sync_value, sender=Sale, dispatch_uid='app.signals.update_sync_value.Sale')

        customer = mixer.blend(Customer, name='Luciano')
        tz = timezone.get_current_timezone()
        self.today = timezone.make_aware(datetime.datetime.today(), tz, True)
        self.sale = mixer.blend(Sale, id=1, date=self.today, customer=customer, price=10000.00)
        sale_installment = mixer.blend(SaleInstallment, sale=self.sale, installment_amount=10000.00, paid_amount=2000.00)

    def test_sale_instance(self):
        self.assertTrue(isinstance(self.sale, Sale))

    def test_sale_str(self):
        # Convert today to UTC because SQLite store date as UTC
        utc_today = self.today.astimezone(timezone.utc)
        self.assertEqual(str(self.sale), f"{utc_today.strftime('%m/%d/%Y')} - Luciano - 1")

    def test_sale_paid_amount(self):
        self.assertEqual(self.sale.paid_amount, 2000.00)

    def test_sale_pending_balance(self):
        self.assertEqual(self.sale.pending_balance, 8000.00)


class SaleProductModelTest(TestCase):

    def setUp(self):
        # Disconnect Signals
        pre_save.disconnect(receiver=preSave_Sale, sender=Sale, dispatch_uid='app.signals.preSave_Sale')
        post_save.disconnect(receiver=postSave_Sale, sender=Sale, dispatch_uid='app.signals.postSave_Sale')
        post_save.disconnect(receiver=update_sync_value, sender=Sale, dispatch_uid='app.signals.update_sync_value.Sale')

        product = mixer.blend(Product, name='Cocina')
        sale = mixer.blend(Sale, id=1)
        self.sale_product = mixer.blend(SaleProduct, sale=sale, product=product, price=2000.00)

    def test_saleproduct_instance(self):
        self.assertTrue(isinstance(self.sale_product, SaleProduct))

    def test_saleproduct_str(self):
        self.assertEqual(str(self.sale_product), '1 - Cocina - 2000.0')


class SaleInstallmentModelTest(TestCase):

    def setUp(self):
        # Disconnect Signals
        pre_save.disconnect(receiver=preSave_Sale, sender=Sale, dispatch_uid='app.signals.preSave_Sale')
        post_save.disconnect(receiver=postSave_Sale, sender=Sale, dispatch_uid='app.signals.postSave_Sale')
        post_save.disconnect(receiver=update_sync_value, sender=Sale, dispatch_uid='app.signals.update_sync_value.Sale')

        sale = mixer.blend(Sale, id=1)
        self.sale_installment = mixer.blend(
            SaleInstallment,
            sale=sale,
            installment=100,
            installment_amount=2000.00,
            paid_amount=0.00
        )

    def test_saleinstallment_instance(self):
        self.assertTrue(isinstance(self.sale_installment, SaleInstallment))

    def test_saleinstallment_str(self):
        self.assertEqual(str(self.sale_installment), '1 - 100')


class LoginLogModelTest(TestCase):

    def setUp(self):
        self.today = datetime.datetime.today()
        self.login_log = mixer.blend(LoginLog, login_datetime=self.today)

    def test_loginlog_instance(self):
        self.assertTrue(isinstance(self.login_log, LoginLog))

    def test_loginlog_str(self):
        # Convert today to UTC because SQLite store date as UTC
        utc_today = self.today.astimezone(timezone.utc)
        self.assertEqual(str(self.login_log), utc_today.strftime('%m/%d/%Y %I:%M %p'))


class KeyValueStoreModelTest(TestCase):

    def setUp(self):
        self.time = time.time()
        self.keyvalue_object = KeyValueStore()
        self.keyvalue_object.set('sync', self.time)

    def test_key_value_store(self):
        self.assertTrue(self.keyvalue_object.get('sync'), self.time)

    def test_key_not_exists(self):
        self.assertIsNone(self.keyvalue_object.get('mykey'))
