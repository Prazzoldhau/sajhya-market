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
    )
    phone = models.CharField(max_length=15)
    license_number = models.CharField(max_length=20, default='temporary')
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='personal'
    )
    personal_code = models.CharField(max_length=15, unique=True, editable=False, null=True, blank=True)
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
    
    def save(self, *args, **kwargs):
        # Only generate a code if it doesn't already exist
        if not self.personal_code:
            # Generate the code outside the transaction to avoid long locks
            self.personal_code = self.generate_personal_code()
            # Now save within a transaction to handle any race condition
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
            except IntegrityError:
                # Very rare: another user saved with the same code at the exact same time
                # Regenerate and retry once
                self.personal_code = self.generate_personal_code()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
    
    def __str__(self):
        return self.username