import math
import time
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from app.models import Sale, SaleInstallment, Customer, KeyValueStore, LoginLog
from collection.models import Collection


@receiver(pre_save, sender=Sale, dispatch_uid='app.signals.preSave_Sale')
def preSave_Sale(sender, instance, *args, **kwargs):
    if instance.id:
        original = Sale.objects.get(pk=instance.id)
        instance.__original_object = original


@receiver(post_save, sender=Sale, dispatch_uid='app.signals.postSave_Sale')
def postSave_Sale(sender, instance, created, **kwargs):
    '''
    THE SAME LOGIC IS USED IN create_sale TEMPLATE
    When a new sale is created:
    1. I check if the price/amount of installments is integer, in which case the amount
       of installments is fixed (fixed_installment_amount). If not, last installment amount is
       different.
    2. If fixed_installment_amount > 0.6 I add a new installment to prevent the last installment to
       be to much higher than the rest of the installments
    '''
    def create_installments():
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

    if created is True:
        create_installments()
    else:
        original_price = instance.__original_object.price
        original_installments = instance.__original_object.installments
        if original_price != instance.price or original_installments != instance.installments:
            SaleInstallment.objects.filter(sale=instance).delete()
            create_installments()


@receiver(post_save, sender=Sale, dispatch_uid='app.signals.update_sync_value.Sale')
@receiver(post_save, sender=Customer, dispatch_uid='app.signals.update_sync_value.Customer')
@receiver(post_save, sender=Collection, dispatch_uid='app.signals.update_sync_value.Collection')
def update_sync_value(sender, instance, created, **kwargs):
    epoc = int(time.time())
    KeyValueStore.set('sync', epoc)


@receiver(user_logged_in)
def userLogged_In(sender, request, user, **kwargs):
    LoginLog.objects.create(user=user)
