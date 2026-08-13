from django.conf import settings
from django.db import models, IntegrityError, transaction
import string
import secrets


class Zone(models.Model):
    """A plain named delivery area (e.g. 'Koteshwor', 'Baneshwor'). No geo
    data -- staff pick these manually, same as every other address field in
    this codebase. Kept as its own model (rather than a hardcoded choices
    list) so new zones can be added from admin without a deploy."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Zones'

    def __str__(self):
        return self.name


class Rider(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('on_delivery', 'On Delivery'),
        ('offline', 'Offline'),
    )
    VEHICLE_CHOICES = (
        ('bike', 'Motorbike'),
        ('bicycle', 'Bicycle'),
        ('on_foot', 'On Foot'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rider_profile'
    )
    rider_code = models.CharField(max_length=15, editable=False, unique=True)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES, default='bike')
    current_zone = models.ForeignKey(
        Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name='riders'
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='offline')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_rider_code(self):
        """Generate a unique rider code like RID-A3F9K2 -- same shape as
        Clinic.generate_clinic_code / Enterprise's equivalent."""
        prefix = "RID-"
        length = 6
        alphabet = string.ascii_uppercase + string.digits
        while True:
            random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
            code = prefix + random_part
            if not Rider.objects.filter(rider_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.rider_code:
            self.rider_code = self.generate_rider_code()
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
            except IntegrityError:
                # Very rare: another rider got the same code at the same microsecond
                self.rider_code = self.generate_rider_code()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rider_code} — {self.user.username}"


class Delivery(models.Model):
    """One parcel to move: created automatically once its Order is
    confirmed (see signals.py), then assigned to a Rider by staff via
    admin. Status is tracked separately from Order.status because it
    describes rider-ops detail (assigned/picked up/in transit) that the
    generic order-status dropdown doesn't capture -- key transitions get
    synced back to Order.status so the existing vendor order views stay
    accurate without any changes there."""
    STATUS_CHOICES = (
        ('unassigned', 'Unassigned'),
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    )

    order = models.OneToOneField(
        'marketplace_app.Order', on_delete=models.CASCADE, related_name='delivery'
    )
    rider = models.ForeignKey(
        Rider, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries'
    )
    pickup_zone = models.ForeignKey(
        Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name='pickups'
    )
    drop_zone = models.ForeignKey(
        Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name='drops'
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='unassigned')

    # Stage 1 assumes every order is COD (Order has no payment-method field
    # yet) -- amount defaults to the order total when the Delivery is created.
    cod_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cod_collected = models.BooleanField(default=False)
    cod_collected_at = models.DateTimeField(null=True, blank=True)

    assigned_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Deliveries'

    def __str__(self):
        return f"Delivery for {self.order.order_number}"
