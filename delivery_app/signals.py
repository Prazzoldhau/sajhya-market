from django.db.models.signals import post_save
from django.dispatch import receiver

from marketplace_app.models import Order
from .models import Delivery, Zone

DEFAULT_PICKUP_ZONE_NAME = 'Sajhya Pickup'


@receiver(post_save, sender=Order)
def create_delivery_on_confirm(sender, instance, **kwargs):
    """Mirrors real Nepali COD practice: once a vendor phone-confirms an
    order (Order.status -> 'confirmed'), it's ready to hand off to the
    delivery pool. Hooks into the existing vendor_order_detail status
    dropdown with zero changes to marketplace_app."""
    if instance.status != 'confirmed':
        return
    if hasattr(instance, 'delivery'):
        return

    default_pickup, _ = Zone.objects.get_or_create(name=DEFAULT_PICKUP_ZONE_NAME)
    Delivery.objects.create(
        order=instance,
        pickup_zone=default_pickup,
        cod_amount=instance.total_amount,
    )
