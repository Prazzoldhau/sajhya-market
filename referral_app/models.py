from django.db import models, IntegrityError, transaction
from django.conf import settings
import secrets, string, pytz
from datetime import datetime
from personal_account.models import AddPatient
from clinic_account.models import Clinic


def get_nepal_time():
    tz = pytz.timezone('Asia/Kathmandu')
    return datetime.now(tz)


class Referral(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    referral_code = models.CharField(max_length=14, editable=False, unique=True)

    # The logged-in user who is sending the referral
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_referrals',
    )

    # Patient info captured at referral time (future: pre-filled by image scanner)
    patient_name = models.CharField(max_length=100)
    patient_contact = models.CharField(max_length=20, blank=True)
    patient_diagnosis = models.CharField(max_length=200)

    # Patient record linked after acceptance
    patient = models.ForeignKey(
        AddPatient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals',
    )

    # The physio/user this referral is directed to (optional — can be claimed by anyone with the code)
    referred_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_referrals',
    )
    referred_to_clinic = models.ForeignKey(
        Clinic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals',
    )

    reason = models.TextField()
    notes = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(default=get_nepal_time)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def generate_referral_code(self):
        prefix = "REF-"
        alphabet = string.ascii_uppercase + string.digits
        while True:
            random_part = ''.join(secrets.choice(alphabet) for _ in range(6))
            code = prefix + random_part
            if not Referral.objects.filter(referral_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        try:
            with transaction.atomic():
                super().save(*args, **kwargs)
        except IntegrityError:
            self.referral_code = self.generate_referral_code()
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.referral_code} — {self.patient_name}"

    @property
    def status_badge_class(self):
        return {
            'pending': 'warning',
            'accepted': 'info',
            'in_progress': 'primary',
            'completed': 'success',
            'rejected': 'danger',
            'cancelled': 'secondary',
        }.get(self.status, 'light')
