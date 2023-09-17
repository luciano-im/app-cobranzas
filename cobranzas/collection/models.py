from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from app.models import Customer, SaleInstallment


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
