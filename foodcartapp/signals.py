from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Order, Restaurant
from .utils import get_or_create_location


@receiver(pre_save, sender=Restaurant)
def update_restaurant_location(sender, instance, **kwargs):
    if instance.pk:
        old = sender.objects.get(pk=instance.pk)
        if old.address != instance.address:
            instance.location = get_or_create_location(instance.address)
    else:
        instance.location = get_or_create_location(instance.address)


@receiver(pre_save, sender=Order)
def update_order_location(sender, instance, **kwargs):
    if instance.pk:
        old = sender.objects.get(pk=instance.pk)
        if old.client_address != instance.client_address:
            instance.location = get_or_create_location(instance.client_address)
    else:
        instance.location = get_or_create_location(instance.client_address)
