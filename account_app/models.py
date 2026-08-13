from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db import IntegrityError, transaction
import secrets
import string

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('personal', 'Personal Account User'),
        ('clinic', 'Clinic User'),
        ('enterprise', 'Enterprise User'),
        ('rider', 'Rider'),
    )
    phone = models.CharField(max_length=15)
    license_number = models.CharField(max_length=20, default='temporary')
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='personal'
    )
    personal_code = models.CharField(max_length=15, unique=True, editable=False, null=True, blank=True)
    # Secret used for the physio's patient-pairing QR (separate from
    # personal_code, which is a semi-public directory identifier shown to
    # clinics searching for a physio -- this one is never displayed anywhere
    # except the pairing QR screen).
    pairing_token = models.CharField(max_length=32, unique=True, editable=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    def generate_personal_code(self):
        """Generate a unique personal code like PER-A3F9K2"""
        prefix = "PER-"
        length = 6
        alphabet = string.ascii_uppercase + string.digits
        while True:
            random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
            code = prefix + random_part
            if not User.objects.filter(personal_code=code).exists():
                return code

    def generate_pairing_token(self):
        return secrets.token_urlsafe(24)

    def save(self, *args, **kwargs):
        # Only generate codes if they don't already exist
        if not self.personal_code:
            self.personal_code = self.generate_personal_code()
        if not self.pairing_token:
            self.pairing_token = self.generate_pairing_token()
        try:
            with transaction.atomic():
                super().save(*args, **kwargs)
        except IntegrityError:
            # Very rare: another user saved with the same code/token at the exact same time
            self.personal_code = self.generate_personal_code()
            self.pairing_token = self.generate_pairing_token()
            super().save(*args, **kwargs)
    
    def __str__(self):
        return self.username