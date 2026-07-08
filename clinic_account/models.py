from django.db import models, IntegrityError, transaction
from django.conf import settings  # or import your User model directly
import string
import secrets


class Clinic(models.Model):
    clinic_name = models.CharField(max_length=255)
    clinic_code = models.CharField(max_length=14, editable=False, unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    pan_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Foreign key to user who created the clinic
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # or models.CASCADE / SET_NULL depending on your need
        related_name='clinics'
    )
    def generate_clinic_code(self):
        """Generate a unique patient code like PAT-A3F9K2"""
        prefix = "CLI-"
        length = 6  # shorter than 10 for readability; adjust as needed
        alphabet = string.ascii_uppercase + string.digits
        while True:
            random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
            code = prefix + random_part
            if not Clinic.objects.filter(clinic_code=code).exists():
                return code
                
    def save(self, *args, **kwargs):
        # Only generate a code if it doesn't already exist
        if not self.clinic_code:
            self.clinic_code = self.generate_clinic_code()
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
            except IntegrityError:
                # Very rare: another patient got the same code at the same microsecond
                self.clinic_code = self.generate_clinic_code()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
    
    
    def __str__(self):
        return self.clinic_name
    
class QueueEntry(models.Model):
    """One patient's spot in a clinic's on-site queue for today."""
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('called', 'Called'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='queue_entries')
    patient = models.ForeignKey('personal_account.AddPatient', on_delete=models.CASCADE, related_name='queue_entries')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='waiting')
    joined_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.patient.patient_name} @ {self.clinic.clinic_name} ({self.status})"


class ClinicPhysio(models.Model):
    """Relationship between a clinic and a physio (who is a personal user)"""
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='registered_clinic')
    physio = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registered_physio')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # if physio still works there
   
    
    
    class Meta:
        unique_together = ['clinic', 'physio']  # prevent double claim