import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class BillingEntry(models.Model):
    """One patient billing line a physio logs for their own daily record --
    a digital version of the paper invoice book (patient name, service,
    rate, payment mode) rather than a formal hospital invoice system.
    Deliberately simple: no insurance/claim fields, no tax lines -- just
    enough to replace the daily paper log and total up the day.

    Scoped to the physio who entered it (like personal_account.AddPatient's
    created_by) -- nobody else can see or edit another physio's entries."""

    PAYMENT_MODE_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('online', 'Online'),
        ('other', 'Other'),
    ]
    SEX_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    physio = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='billing_entries'
    )
    entry_date = models.DateField(default=timezone.localdate)
    patient_name = models.CharField(max_length=200)
    age = models.PositiveIntegerField(null=True, blank=True)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    service = models.CharField(max_length=150, default='Physiotherapy')
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODE_CHOICES, default='cash')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-entry_date', '-created_at']
        verbose_name_plural = 'Billing entries'

    def __str__(self):
        return f"{self.invoice_number} — {self.patient_name} ({self.entry_date})"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"BILL-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
