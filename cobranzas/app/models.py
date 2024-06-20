import datetime
from django.utils import timezone
import json
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    is_collector = models.BooleanField(default=False, verbose_name=_('Is a collector?'))

    @cached_property
    @admin.display(description=_("Is it an administrator?"))
    def is_admin(self):
        return self.is_staff

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Customer(models.Model):
    CITY = (
        ('ARR', 'Arrecifes'),
        ('SAR', 'Capitan Sarmiento'),
        ('DUG', 'Duggan'),
        ('LUI', 'La Luisa'),
        ('SAL', 'Salto'),
        ('VLI', 'Villa Lía'),
    )

    name = models.CharField(max_length=150, db_index=True, verbose_name=_('Client Name'))
    address = models.CharField(max_length=150, blank=True, null=True, verbose_name=_('Address'))
    city = models.CharField(max_length=50, choices=CITY, verbose_name=_('City'))
    telephone = models.CharField(max_length=150, blank=True, null=True, verbose_name=_('Telephone'))
    collector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Collector'))

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True, verbose_name=_('Name'))
    brand = models.CharField(max_length=255, db_index=True, verbose_name=_('Brand'))
    price = models.FloatField(default=0.00, verbose_name=_('Price'))
    sku = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('SKU'))

    def __str__(self):
        return f'{self.pk} - {self.name} {self.brand}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['brand', 'sku'], name='unique_product'
            ),
        ]


class Sale(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('User'))
    customer = models.ForeignKey(Customer, db_index=True, on_delete=models.CASCADE, verbose_name=_('Customer'))
    price = models.FloatField(verbose_name=_('Price'))
    installment_amount = models.FloatField(verbose_name=_('Installment Amount'))
    installments = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Installments')
    )
    date = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('Date'))
    modification = models.DateTimeField(auto_now=True, verbose_name=_('Modification Date'))
    sale_date = models.DateTimeField(db_index=True, verbose_name=_('Sale Date'))
    collector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='collector', verbose_name=_('Collector'))
    uncollectible = models.BooleanField(default=False, verbose_name=_('Is uncollectible?'))
    remarks = models.TextField(default="", verbose_name=_('Remarks'))

    def __str__(self):
        return f"{self.sale_date.strftime('%m/%d/%Y')} - {self.customer.name} - {self.pk}"

    @cached_property
    @admin.display(description=_("Pending Balance"))
    def pending_balance(self):
        return self.price - self.paid_amount

    @cached_property
    @admin.display(description=_("Paid Amount"))
    def paid_amount(self):
        paid = SaleInstallment.objects.filter(sale=self.id).aggregate(paid=Sum('paid_amount'))
        return paid['paid']


class SaleProduct(models.Model):
    sale = models.ForeignKey(Sale, db_index=True, on_delete=models.CASCADE, verbose_name=_('Sale'))
    product = models.ForeignKey(Product, db_index=True, on_delete=models.RESTRICT, verbose_name=_('Product'))
    price = models.FloatField(verbose_name=_('Unit Price'))

    def __str__(self):
        return f'{self.sale.pk} - {self.product.name} - {self.price}'


class SaleInstallment(models.Model):
    PAID = 'PAID'
    PENDING = 'PENDING'
    PARTIAL = 'PARTIAL'
    STATUS = (
        (PAID, _('Paid')),
        (PENDING, _('Pending')),
        (PARTIAL, _('Partially Paid')),
    )

    sale = models.ForeignKey(Sale, db_index=True, on_delete=models.CASCADE, verbose_name=_('Sale'))
    installment = models.IntegerField(db_index=True, verbose_name=_('Installment'))
    installment_amount = models.FloatField(verbose_name=_('Installment Amount'))
    paid_amount = models.FloatField(default=0.0, verbose_name=_('Paid Amount'))
    payment_date = models.DateTimeField(blank=True, null=True, verbose_name=_('Payment Date'))
    status = models.CharField(
        max_length=50, default=PENDING, choices=STATUS, db_index=True, verbose_name=_('Payment Status')
    )

    def __str__(self):
        return f'{self.sale.pk} - {self.installment}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sale', 'installment'], name='unique_sale_installment'
            ),
            models.CheckConstraint(
                name='paid_amount_less_or_equal_than_installment_amount',
                check=models.Q(paid_amount__lte=models.F('installment_amount')),
            ),
        ]


class LoginLog(models.Model):
    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE, verbose_name=_('User'))
    login_datetime = models.DateTimeField(auto_now_add=True, verbose_name=_('Login Date/Time'))

    def __str__(self):
        return self.login_datetime.strftime('%m/%d/%Y %I:%M %p')

    class Meta:
        verbose_name = _('Login Log')


class KeyValueStore(models.Model):
    key = models.CharField(max_length=50)
    value = models.CharField(max_length=250)

    @classmethod
    def set(self, key, value):
        obj = None
        val = {'value': value}
        try:
            obj = self.objects.get(key=key)
        except:
            obj = KeyValueStore(key=key)

        obj.value = json.dumps(val)
        obj.save()

    @classmethod
    def get(self, key):
        try:
            obj = json.loads(self.objects.get(key=key).value)
            return obj['value']
        except:
            return None

    def __str__(self):
        return f'{self.key}'
