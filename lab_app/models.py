import uuid
from decimal import Decimal
from django.db import models


class LabTest(models.Model):
    """A blood investigation a patient can request from the app. Catalog
    is admin-managed (not hardcoded in the app) so prices, wording, and
    the test list itself can change without an app release -- same
    reasoning as personal_account.DiagnosisCode.

    IMPORTANT: seeded with a starter list of common blood tests and
    placeholder prices (see seed_lab_tests) -- review and reprice in
    Django admin before this is used for real requests."""
    CATEGORY_CHOICES = [
        ('hematology', 'Hematology'),
        ('biochemistry', 'Biochemistry'),
        ('hormonal', 'Hormonal'),
        ('serology', 'Serology / Infection'),
        ('electrolytes', 'Electrolytes & Minerals'),
        ('urine', 'Urine'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sample_type = models.CharField(max_length=100, blank=True, help_text='e.g. "Blood - Venous"')
    prep_instructions = models.CharField(max_length=255, blank=True, help_text='e.g. "8-12 hours fasting required"')
    turnaround_time = models.CharField(max_length=100, blank=True, help_text='e.g. "Same day", "24 hours"')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class LabTestPanel(models.Model):
    """A bundled group of LabTests sold together at one price -- e.g.
    'Diabetes Panel', 'Fever Panel' (the same panels real Nepali diagnostic
    labs market as fixed-price packages). `price` is set by admin, normally
    at a discount vs buying each included test separately -- a_la_carte_total
    and savings below are computed for "you save Rs X" messaging on the
    storefront, not stored."""
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    tests = models.ManyToManyField(LabTest, related_name='panels')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def a_la_carte_total(self):
        return sum((t.price for t in self.tests.all()), Decimal('0.00'))

    @property
    def savings(self):
        return self.a_la_carte_total - self.price


class LabTestRequest(models.Model):
    """A patient's submitted request for one or more blood tests --
    mirrors marketplace_app.Order's shape (order_number pattern, status
    workflow, snapshot line items) since it's the same kind of
    patient-submits/clinic-processes flow."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sample_collected', 'Sample Collected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    request_number = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey(
        'personal_account.AddPatient', on_delete=models.CASCADE, related_name='lab_requests'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Lab Request #{self.request_number} — {self.patient.patient_name}"

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = f"LAB-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class LabTestRequestItem(models.Model):
    """One test within a request. Snapshots name/price at request time
    (like marketplace_app.OrderItem) so a later catalog price change
    doesn't rewrite the history of what a patient actually requested."""
    request = models.ForeignKey(LabTestRequest, on_delete=models.CASCADE, related_name='items')
    lab_test = models.ForeignKey(LabTest, on_delete=models.SET_NULL, null=True, blank=True)
    test_name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.test_name
