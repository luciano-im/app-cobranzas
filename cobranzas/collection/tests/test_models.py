import datetime

from mixer.backend.django import mixer

from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.test import TestCase
from django.utils import timezone

from app.models import User, Customer, Sale, SaleInstallment
from collection.models import Collection, CollectionInstallment, CollectorSyncLog

from app.signals import preSave_Sale, postSave_Sale, update_sync_value


class CollectionModelTest(TestCase):

    def setUp(self):
        # Disconnect Signals
        post_save.disconnect(receiver=update_sync_value, sender=Customer, dispatch_uid='app.signals.update_sync_value.Customer')
        post_save.disconnect(receiver=update_sync_value, sender=Collection, dispatch_uid='app.signals.update_sync_value.Collection')

        collector = User.objects.create_user(username='luciano', email='test@test.com', password='mypassword', is_collector=True)
        customer = Customer.objects.create(
            name='Autoservicio Marcos',
            address='Mi Direccion 1234',
            city='ARR',
            telephone='2478505050',
            collector=collector
        )
        tz = timezone.get_current_timezone()
        self.today = timezone.make_aware(datetime.datetime.today(), tz, True)
        self.collection = mixer.blend(Collection, id=1, collector=collector, customer=customer, date=self.today)

    def test_collection_instance(self):
        self.assertTrue(isinstance(self.collection, Collection))

    def test_collection_str(self):
        # Convert today to UTC because SQLite store date as UTC
        utc_today = self.today.astimezone(timezone.utc)
        self.assertEqual(str(self.collection), f"1: Autoservicio Marcos - {utc_today.strftime('%m/%d/%Y')}")


class CollectionInstallmentModelTest(TestCase):

    def setUp(self):
        # Disconnect Signals
        post_save.disconnect(receiver=update_sync_value, sender=Collection, dispatch_uid='app.signals.update_sync_value.Collection')
        pre_save.disconnect(receiver=preSave_Sale, sender=Sale, dispatch_uid='app.signals.preSave_Sale')
        post_save.disconnect(receiver=postSave_Sale, sender=Sale, dispatch_uid='app.signals.postSave_Sale')
        post_save.disconnect(receiver=update_sync_value, sender=Sale, dispatch_uid='app.signals.update_sync_value.Sale')

        collection = mixer.blend(Collection, id=1)
        sale = mixer.blend(Sale, id=5)
        sale_installment = mixer.blend(SaleInstallment, sale=sale, installment=12, installment_amount=10000.00, paid_amount=2000.00)
        self.collection_installment = mixer.blend(CollectionInstallment, id=3, collection=collection, sale_installment=sale_installment, amount=2000.00)

    def test_collectioninstallment_instance(self):
        self.assertTrue(isinstance(self.collection_installment, CollectionInstallment))

    def test_collectioninstallment_str(self):
        self.assertEqual(str(self.collection_installment), "3: 1 - 5 - 12 - 2000.0")

    def test_collectioninstallment_clean_validation(self):
        self.collection_installment.amount = 20000.00
        self.assertRaises(ValidationError, self.collection_installment.clean)


class CollectorSyncLogModelTest(TestCase):

    def setUp(self):
        self.today = datetime.datetime.today()
        self.collector_sync_log = mixer.blend(CollectorSyncLog, sync_datetime=self.today)

    def test_collectorsync_instance(self):
        self.assertTrue(isinstance(self.collector_sync_log, CollectorSyncLog))

    def test_loginlog_str(self):
        # Convert today to UTC because SQLite store date as UTC
        utc_today = self.today.astimezone(timezone.utc)
        self.assertEqual(str(self.collector_sync_log), utc_today.strftime('%m/%d/%Y %I:%M %p'))
