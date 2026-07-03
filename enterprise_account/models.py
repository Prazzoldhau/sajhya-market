from django.db import models, IntegrityError, transaction
from django.conf import settings
import string
import secrets
import pytz
from datetime import datetime

from clinic_account.models import Clinic


def get_nepal_time():
    tz = pytz.timezone('Asia/Kathmandu')
    return datetime.now(tz)


class Enterprise(models.Model):
    enterprise_name = models.CharField(max_length=255)
    enterprise_code = models.CharField(max_length=14, editable=False, unique=True)
    registration_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

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


class Department(models.Model):
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name='departments')
    department_name = models.CharField(max_length=100)
    department_code = models.CharField(max_length=14, editable=False, unique=True)

    # Denormalized convenience pointer to the current HOD; EnterpriseStaff is
    # the authoritative source for role/membership, this is kept in sync by
    # the view layer whenever an HOD assignment changes.
    hod = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hod_of_departments',
    )

    created_at = models.DateTimeField(default=get_nepal_time)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='departments_created',
    )

    class Meta:
        unique_together = ['enterprise', 'department_name']

    def generate_department_code(self):
        """Generate a unique department code like DPT-A3F9K2"""
        prefix = "DPT-"
        length = 6
        alphabet = string.ascii_uppercase + string.digits
        while True:
            random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
            code = prefix + random_part
            if not Department.objects.filter(department_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.department_code:
            self.department_code = self.generate_department_code()
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
            except IntegrityError:
                self.department_code = self.generate_department_code()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.department_name} ({self.enterprise.enterprise_name})"


class EnterpriseStaff(models.Model):
    """Relationship between an Enterprise, a user, and their role.

    Mirrors clinic_account.ClinicPhysio's membership-row style rather than
    Django Groups/Permissions, which this codebase doesn't use anywhere.
    """
    ROLE_CHOICES = [
        ('admin', 'Enterprise Admin'),
        ('hod', 'Head of Department'),
        ('staff', 'Department Staff'),
    ]

    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enterprise_memberships')
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='staff_members',
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['enterprise', 'user']

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} @ {self.enterprise.enterprise_name}"


class DepartmentClinic(models.Model):
    """Attaches an existing Clinic to a Department.

    A many-to-many join (mirrors ClinicPhysio/EnterpriseStaff) rather than a
    single FK on Department, since one department can have several attached
    clinics and a clinic owner can independently also be enterprise staff.
    Clinic ownership (Clinic.created_by) and org membership (EnterpriseStaff)
    stay decoupled; this table only records "this clinic's patients/features
    are visible from this department".
    """
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='attached_clinics')
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='enterprise_departments')
    attached_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='clinic_attachments',
    )
    is_active = models.BooleanField(default=True)
    attached_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['department', 'clinic']

    def __str__(self):
        return f"{self.clinic.clinic_name} -> {self.department.department_name}"
