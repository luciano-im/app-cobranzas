from django.db.models.signals import pre_save, post_save

from mixer.backend.django import mixer

from collection.templatetags.get_sale_products import get_sale_products

from app.models import Product, Sale, SaleProduct
from app.signals import preSave_Sale, postSave_Sale, update_sync_value

from django.test import TestCase


class GetSaleProductsTest(TestCase):

    def setUp(self):
        # Disconnect Signals
        pre_save.disconnect(receiver=preSave_Sale, sender=Sale, dispatch_uid='app.signals.preSave_Sale')
        post_save.disconnect(receiver=postSave_Sale, sender=Sale, dispatch_uid='app.signals.postSave_Sale')
        post_save.disconnect(receiver=update_sync_value, sender=Sale, dispatch_uid='app.signals.update_sync_value.Sale')

        self.sale_id = 1

        product_cocina = mixer.blend(Product, name='Cocina')
        product_heladera = mixer.blend(Product, name='Heladera')
        sale = mixer.blend(Sale, id=self.sale_id)
        SaleProduct.objects.create(sale=sale, product=product_cocina, price=2000.00)
        SaleProduct.objects.create(sale=sale, product=product_heladera, price=10000.00)

    def test_sale_products(self):
        result = ['Cocina', 'Heladera']
        self.assertEqual(get_sale_products(self.sale_id), result)
