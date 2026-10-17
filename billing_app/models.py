import uuid
from datetime import timedelta
from decimal import Decimal
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


class PatientPackage(models.Model):
    """A subscription package a physio sells a specific patient -- a fixed
    duration (1/2/3 weeks or 1 month) and session count for a flat price.
    Unlike BillingEntry above (a free-text daily paper-log replacement,
    not tied to a real patient record), this is tied to an actual
    AddPatient and tracks session usage against it.

    Deliberately session-count tracking only (not a computed per-session
    currency split, e.g. "NPR 750 used so far") -- that invites rounding/
    fraction noise for no real benefit. Money tracking is instead a
    separate paid-vs-due ledger (see amount_paid/amount_due/PackagePayment
    below), since a patient often pays a package off only partially at
    booking and settles the rest later, in one or more further payments --
    unrelated to how many sessions they've used.

    sessions_used increments by one each time a TreatmentSession is
    logged for this patient while this package is the active one (see
    prescription_app.views.save_treatment_session) -- so "a session" for
    billing purposes is exactly the same thing the physio already means
    by "logging today's session" on the Rx page, not a separate
    checklist to keep in sync."""

    DURATION_CHOICES = [
        ('1_week', '1 Week'),
        ('2_week', '2 Weeks'),
        ('3_week', '3 Weeks'),
        ('1_month', '1 Month'),
    ]
    DURATION_DAYS = {'1_week': 7, '2_week': 14, '3_week': 21, '1_month': 30}

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        'personal_account.AddPatient', on_delete=models.CASCADE, related_name='packages',
    )
    physio = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_packages',
    )
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES)
    total_sessions = models.PositiveIntegerField(help_text='How many sessions this package covers')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sessions_used = models.PositiveIntegerField(default=0)
    start_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    notes = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_duration_display()} package — {self.patient.patient_name} ({self.sessions_used}/{self.total_sessions})"

    @property
    def end_date(self):
        return self.start_date + timedelta(days=self.DURATION_DAYS[self.duration])

    @property
    def sessions_remaining(self):
        return max(0, self.total_sessions - self.sessions_used)

    @property
    def is_expired(self):
        return self.status == 'active' and timezone.localdate() > self.end_date

    @property
    def effective_status(self):
        """status, but auto-showing "completed"/"expired" once the raw
        field is stale -- same derive-don't-schedule-a-job pattern as
        Rx.effective_status in personal_account.models."""
        if self.status == 'active' and self.sessions_used >= self.total_sessions:
            return 'completed'
        if self.status == 'active' and self.is_expired:
            return 'expired'
        return self.status

    @property
    def effective_status_display(self):
        if self.effective_status == 'expired':
            return 'Expired'
        return self.get_status_display()

    @property
    def amount_due(self):
        return max(Decimal('0'), self.total_amount - self.amount_paid)

    @property
    def is_fully_paid(self):
        return self.amount_due <= 0

    def record_session(self):
        """Deducts one session from this package. No-op (returns False)
        if the package isn't actually active -- callers don't need to
        check effective_status themselves first."""
        if self.effective_status != 'active':
            return False
        self.sessions_used += 1
        if self.sessions_used >= self.total_sessions:
            self.status = 'completed'
        self.save()
        return True

    def record_payment(self, amount, payment_mode='cash', notes='', recorded_by=None):
        """Logs one payment against this package's due balance -- used
        both for an initial partial payment at booking and for any
        later installment that settles the rest. Capped at amount_due
        so a mistaken overpayment can't push the balance negative;
        returns None (no-op) for a non-positive amount or once nothing
        is owed."""
        if amount is None or amount <= 0 or self.is_fully_paid:
            return None
        amount = min(Decimal(amount), self.amount_due)
        payment = PackagePayment.objects.create(
            package=self, amount=amount, payment_mode=payment_mode,
            notes=notes, recorded_by=recorded_by,
        )
        self.amount_paid += amount
        self.save()
        return payment


class PackagePayment(models.Model):
    """One payment transaction against a PatientPackage's total_amount.
    A package is often paid off over more than one sitting -- a partial
    payment at booking, the rest later -- so this is a running ledger,
    not just a single amount_paid field, mirroring how BillingEntry
    already logs individual transactions rather than a bare total."""

    package = models.ForeignKey(PatientPackage, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=10, choices=BillingEntry.PAYMENT_MODE_CHOICES, default='cash')
    notes = models.CharField(max_length=255, blank=True, default='')
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"NPR {self.amount} — {self.package}"
