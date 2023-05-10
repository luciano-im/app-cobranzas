import math
import time
from django.db.models.signals import post_save
from django.dispatch import receiver
from app.models import Sale, SaleInstallment, Customer, Collection, KeyValueStore


@receiver(post_save, sender=Sale, dispatch_uid='app.signals.postSave_Sale')
def postSave_User(sender, instance, created, **kwargs):
    '''
    THE SAME LOGIC IS USED IN create_sale TEMPLATE
    When a new sale is created:
    1. I check if the price/amount of installments is integer, in which case the amount
       of installments is fixed (fixed_installment_amount). If not, last installment amount is
       different.
    2. If fixed_installment_amount > 0.6 I add a new installment to prevent the last installment to
       be to much higher than the rest of the installments
    '''

    if created is True:
        price = instance.price
        installment_amount = instance.installment_amount
        installments = price / installment_amount
        fixed_installment_amount = installments - math.trunc(installments)

        if(fixed_installment_amount == 0):
            # Fixed amount is True
            objs = [SaleInstallment(sale=instance, installment=x, installment_amount=instance.installment_amount) for x in range(1, instance.installments + 1)]
            SaleInstallment.objects.bulk_create(objs)
        else:
            # Insallment amount change for the last installment
            installments_quantity = math.trunc(installments)

            # Calculate how many istallments the sale have
            if(fixed_installment_amount <= 0.6):
                installments_quantity -= 1

            last_installment_number = installments_quantity + 1
            last_installment_amount = price - (installments_quantity * installment_amount)

            # Fixed amount installments
            objs = [SaleInstallment(sale=instance, installment=x, installment_amount=instance.installment_amount) for x in range(1, installments_quantity + 1)]
            # Last installment
            objs.append(SaleInstallment(sale=instance, installment=last_installment_number, installment_amount=last_installment_amount))
            SaleInstallment.objects.bulk_create(objs)


@receiver(post_save, sender=Sale, dispatch_uid='app.signals.update_sync_value.Sale')
@receiver(post_save, sender=Customer, dispatch_uid='app.signals.update_sync_value.Customer')
@receiver(post_save, sender=Collection, dispatch_uid='app.signals.update_sync_value.Collection')
def update_sync_value(sender, instance, created, **kwargs):
    epoc = int(time.time())
    KeyValueStore.set('sync', epoc)
