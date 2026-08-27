import uuid
from django.db import models


class DonatableCategory(models.Model):
    """One kind of mobility/disability aid Sajhya is collecting for reuse --
    Wheelchair, Crutches, Walker, etc. Admin-managed like LabTest/marketplace
    Category, so the accepted-items list can change without an app release.

    `image` is a real upload (not the static-path convention marketplace
    Product/PharmacyProduct use) -- this list was seeded with no photos on
    purpose, meant to be filled in later straight from Django admin rather
    than requiring a code change + redeploy for every item photo."""
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, help_text='e.g. "Any size, working condition preferred"')
    image = models.ImageField(upload_to='donate/items/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Donatable categories'

    def __str__(self):
        return self.name


class DonationPledge(models.Model):
    """One donor's submitted offer -- mirrors LabTestRequest's shape
    (auto-numbered, status workflow, contact fields collected inline since
    there's no login for this flow) since it's the same submit/organization-
    follows-up pattern. No pricing here at all -- this isn't a sale."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('contacted', 'Contacted'),
        ('collected', 'Collected'),
        ('cancelled', 'Cancelled'),
    ]

    pledge_number = models.CharField(max_length=20, unique=True, editable=False)
    donor_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    items = models.ManyToManyField(DonatableCategory, related_name='pledges', blank=True)
    notes = models.TextField(blank=True, help_text='Condition, quantity, or items not in the list above')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.pledge_number} — {self.donor_name}"

    def save(self, *args, **kwargs):
        if not self.pledge_number:
            self.pledge_number = f"DON-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
