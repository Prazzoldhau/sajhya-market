from django.db import models, IntegrityError, transaction
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
import random
import string
import secrets


class Enterprise(models.Model):
    enterprise_name = models.CharField(max_length=255)
    enterprise_code = models.CharField(max_length=14, editable=False, unique=True)
    pan_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='enterprises',
    )

    def generate_enterprise_code(self):
        """Generate a unique enterprise code like ENT-A3F9K2"""
        prefix = "ENT-"
        length = 6
        alphabet = string.ascii_uppercase + string.digits
        while True:
            random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
            code = prefix + random_part
            if not Enterprise.objects.filter(enterprise_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.enterprise_code:
            self.enterprise_code = self.generate_enterprise_code()
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
            except IntegrityError:
                self.enterprise_code = self.generate_enterprise_code()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.enterprise_name


class EnterpriseStaff(models.Model):
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name='registered_enterprise')
    physio = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registered_enterprise_physio')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['enterprise', 'physio']

    def __str__(self):
        return f"{self.physio.username} @ {self.enterprise.enterprise_name}"


class Ward(models.Model):
    WARD_TYPE_CHOICES = [
        ('icu', 'ICU'),
        ('hdu', 'HDU'),
        ('surgical', 'Surgical'),
        ('medical', 'Medical'),
        ('ccu', 'CCU'),
        ('general', 'General'),
        ('emergency', 'Emergency'),
        ('maternity', 'Maternity'),
    ]

    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name='wards')
    ward_type = models.CharField(max_length=10, choices=WARD_TYPE_CHOICES, default='general')

    # A shared ICU/HDU computer bookmarks this ward's request-form URL, which
    # is keyed by access_token rather than the ward's id so it isn't guessable
    # by incrementing a number. The PIN is a second factor in case the
    # bookmark/URL itself ever leaks -- same two-layer approach as
    # summit_app.Table (number in the URL + a PIN), just token instead of a
    # small sequential number since wards aren't chosen from a public list.
    access_token = models.CharField(max_length=24, unique=True, editable=False)
    pin_hash = models.CharField(max_length=128, blank=True)
    pin = models.CharField(
        max_length=10,
        blank=True,
        help_text="Plaintext copy shown to the enterprise owner. Login still checks pin_hash.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wards_created',
    )

    class Meta:
        unique_together = ['enterprise', 'ward_type']

    def generate_access_token(self):
        while True:
            token = secrets.token_urlsafe(12)
            if not Ward.objects.filter(access_token=token).exists():
                return token

    def generate_pin(self):
        return f"{random.randint(0, 999999):06d}"

    def set_pin(self, raw_pin):
        self.pin = raw_pin
        self.pin_hash = make_password(raw_pin)

    def check_pin(self, raw_pin):
        return check_password(raw_pin, self.pin_hash)

    def save(self, *args, **kwargs):
        if not self.access_token:
            self.access_token = self.generate_access_token()
        if not self.pin_hash:
            self.set_pin(self.generate_pin())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_ward_type_display()} ({self.enterprise.enterprise_name})"


class PhysioRequest(models.Model):
    URGENCY_CHOICES = [
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('seen', 'Seen'),
        ('noted', 'Noted'),
        ('handled', 'Handled'),
    ]

    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='physio_requests')
    patient_name = models.CharField(max_length=100)
    bed_number = models.CharField(max_length=20, blank=True)
    reason = models.TextField()
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='routine')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    # Message from the physio department back to the ward -- shown on the
    # ward's own request table, so staff there know something happened
    # without having to call anyone.
    physio_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    status_updated_at = models.DateTimeField(null=True, blank=True)
    status_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='physio_requests_updated',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient_name} ({self.ward.get_ward_type_display()}) - {self.get_status_display()}"
