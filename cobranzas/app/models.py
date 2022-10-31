from tabnanny import verbose
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    is_collector = models.BooleanField(default=False, verbose_name=_('Is a collector?'))

    @cached_property
    def is_admin(self):
        return self.is_staff


class Customer(models.Model):
    CITY = (
        ('ARR', 'Arrecifes'),
        ('SAR', 'Capitan Sarmiento'),
        ('SAL', 'Salto'),
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

    def __str__(self):
        return f'{self.date} - {self.customer.name} - {self.pk}'

    @cached_property
    def pending_balance(self):
        return self.price - self.paid_amount

    @cached_property
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


class Collection(models.Model):
    collector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Collector'))
    customer = models.ForeignKey(Customer, db_index=True, on_delete=models.CASCADE, verbose_name=_('Customer'))
    date = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('Date'))
    modification = models.DateTimeField(auto_now=True, verbose_name=_('Modification Date'))

    def __str__(self):
        return f'{self.id}: {self.customer} - {self.date}'


class CollectionInstallment(models.Model):
    collection = models.ForeignKey(Collection, db_index=True, on_delete=models.CASCADE, verbose_name=_('Collection'))
    sale_installment = models.ForeignKey(SaleInstallment, db_index=True, on_delete=models.CASCADE, verbose_name=_('Sale Installment'))
    amount = models.FloatField(verbose_name=_('Amount'))

    def __str__(self):
        return f'{self.id}: {self.collection} - {self.sale_installment} - {self.amount}'

    # Validate SaleInstallment before saving a Collection
    def clean(self):
        if self.amount > self.sale_installment.installment_amount:
            raise ValidationError(
                {'amount': _('Amount can not be greater than installment total amount')}
            )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sale_installment', 'collection'], name='unique_collection'
            ),
        ]