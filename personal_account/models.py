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

    # Only set for patients who signed themselves up from the app (see
    # patient_api_signup) and chose their own password. Physio-created
    # patients keep logging in with patient_code + patient_contact as
    # before; this field being set is what tells patient_api_login to
    # check the hashed password instead of the legacy phone-as-PIN.
    password = models.CharField(max_length=128, null=True, blank=True, help_text='Hashed, never stored in plain text')

    # Foreign key points to the user who created the patient. Nullable because
    # self-registered patients (from the patient-facing app) have no creating
    # physio -- they get linked via PatientPhysioPairing instead.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
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

    # Set when the patient deletes their own account from the app (see
    # patient_app.views.patient_api_delete_account). The row is anonymised in
    # place rather than dropped: prescriptions, session notes and orders hang
    # off it, and those are clinical and financial records the practice has to
    # keep. Everything that identifies the person -- name, contact, password,
    # QR token -- is cleared at the same time, so what remains is not personal
    # data. Every login path must refuse a patient with is_deleted set.
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def anonymise_for_deletion(self):
        """Strip personal data and lock the account out, keeping the row so
        linked clinical/financial records stay intact. Callers are responsible
        for deleting the related app-side data (push subscriptions, physio
        pairings, product recommendations) and flushing the session.

        Deliberately writes via queryset.update() rather than save(): save()
        regenerates qr_token and qr_code whenever they are falsy, so clearing
        them and saving would immediately hand the deleted account a working
        QR login token back.
        """
        type(self).objects.filter(pk=self.pk).update(
            patient_name='Deleted patient',
            patient_contact='',
            password=None,
            qr_token=None,
            qr_code=None,
            activation_expires_at=None,
            is_deleted=True,
            deleted_at=get_nepal_time(),
        )
        self.refresh_from_db()

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


class PatientPhysioPairing(models.Model):
    """Links a patient to a physio who can access them. AddPatient.created_by
    is the *creator* of the patient record (nullable for self-registered
    patients); this table is the general-purpose patient<->physio access map,
    covering physio-created, referral, and self-registration-via-QR cases."""

    SOURCE_CHOICES = (
        ('self_registered_qr', 'Self-registered via QR'),
        ('physio_created', 'Physio-created'),
        ('referral', 'Referral'),
    )

    patient = models.ForeignKey(AddPatient, on_delete=models.CASCADE, related_name='pairings')
    physio = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_pairings')
    clinic = models.ForeignKey(Clinic, on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_pairings')
    enterprise = models.ForeignKey(Enterprise, on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_pairings')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    paired_at = models.DateTimeField(default=get_nepal_time)

    class Meta:
        unique_together = ('patient', 'physio')

    def __str__(self):
        return f"{self.patient.patient_code} <-> {self.physio_id} ({self.source})"


