from django.db import models, IntegrityError, transaction
from django.conf import settings
import secrets, string,pytz
from datetime import datetime
from clinic_account.models import Clinic
from enterprise_account.models import Enterprise
from django.db import models
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from qrcode import make as make_qr
from io import BytesIO

def get_nepal_time():
    tz = pytz.timezone('Asia/Kathmandu')
    return datetime.now(tz)


class AddPatient(models.Model):
    patient_code = models.CharField(max_length=14, editable=False, unique=True)
    patient_name = models.CharField(max_length=50)
    patient_contact = models.CharField(max_length=50)
    completed_session = models.IntegerField(default=0)
    patient_diagnosis = models.CharField(max_length=100)
    qr_code = models.URLField(blank=True, null=True)  # store the image URL
    qr_token = models.CharField(max_length=32,null=True, editable=False, unique=True, blank=True)
    activation_expires_at = models.DateTimeField(null=True, blank=True)
        
    # Foreign key points to the user who created the patient
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='physio_assigned'
    )
    
        # Foreign key points to the clinic where patient is created
    origin_clinic = models.ForeignKey(
        Clinic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clinic_assigned'
    )

        # Foreign key points to the enterprise (hospital) where patient is created
    origin_enterprise = models.ForeignKey(
        Enterprise,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enterprise_assigned'
    )

    created_at = models.DateTimeField(default=get_nepal_time)
    def generate_patient_code(self):
        prefix = "PAT-"
        length = 6  # shorter than 10 for readability; adjust as needed
        alphabet = string.ascii_uppercase + string.digits
        while True:
            random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
            code = prefix + random_part
            if not AddPatient.objects.filter(patient_code=code).exists():
                return code
    def generate_qr_token(self):
        return secrets.token_urlsafe(24)

    def generate_qr_code(self):
        raw_data = self.qr_token
        qr_img = make_qr(raw_data)
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)

        filename = f"qr_codes/{self.patient_code}.png"
        path = default_storage.save(filename, ContentFile(buffer.read()))
        return default_storage.url(path)

    def save(self, *args, **kwargs):
        if not self.patient_code:
            self.patient_code = self.generate_patient_code()
        if not self.qr_token:
            self.qr_token = self.generate_qr_token()
        if not self.qr_code:
            self.qr_code = self.generate_qr_code()
        
        try:
            with transaction.atomic():
                super().save(*args, **kwargs)
        except IntegrityError:
            self.patient_code = self.generate_patient_code()
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_name} ({self.patient_code})"

    @property
    def is_activation_active(self):
        return bool(self.activation_expires_at and self.activation_expires_at > get_nepal_time())


class ActivationCard(models.Model):
    """A single-use recharge-card-style code that grants a patient
    `duration_days` of app access when redeemed (see AddPatient.
    activation_expires_at). Sold as a Product like anything else in the
    shop; the physical/printed card carries both this code as text and
    as a QR (see generate_qr_code) so it can be typed or scanned."""

    code = models.CharField(max_length=20, unique=True, editable=False)
    qr_code = models.URLField(blank=True, null=True)
    duration_days = models.PositiveIntegerField(default=30)

    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(
        AddPatient, on_delete=models.SET_NULL, null=True, blank=True, related_name='activation_cards'
    )
    used_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def generate_code(self):
        # Unambiguous alphabet (no 0/O, 1/I/L) grouped like a recharge card,
        # e.g. A3F7-K9P2-XQ4M - short enough to type by hand if the QR
        # can't be scanned.
        alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
        while True:
            raw = ''.join(secrets.choice(alphabet) for _ in range(12))
            code = '-'.join(raw[i:i + 4] for i in range(0, 12, 4))
            if not ActivationCard.objects.filter(code=code).exists():
                return code

    def generate_qr_code(self):
        qr_img = make_qr(self.code)
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)

        filename = f"activation_codes/{self.code}.png"
        path = default_storage.save(filename, ContentFile(buffer.read()))
        return default_storage.url(path)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.qr_code:
            self.qr_code = self.generate_qr_code()

        try:
            with transaction.atomic():
                super().save(*args, **kwargs)
        except IntegrityError:
            self.code = self.generate_code()
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} ({'used' if self.is_used else 'unused'})"


