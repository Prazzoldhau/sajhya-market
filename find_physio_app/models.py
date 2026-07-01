from django.db import models
from django.conf import settings
from django.db.models import Avg


class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PhysioProfile(models.Model):
    physio = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='physio_profile'
    )
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='physio_photos/', null=True, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=200, blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    home_visit_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=200)
    travel_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    specializations = models.ManyToManyField(Specialization, blank=True)
    is_home_visit = models.BooleanField(default=False)
    is_clinic_visit = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.physio.get_full_name() or self.physio.username} — Profile"

    def clinic_total(self):
        return self.consultation_fee + self.platform_fee

    def home_total(self):
        return self.home_visit_fee + self.platform_fee + self.travel_cost

    def star_range(self):
        return range(1, 6)


DAY_CHOICES = [
    (0, 'Sunday'),
    (1, 'Monday'),
    (2, 'Tuesday'),
    (3, 'Wednesday'),
    (4, 'Thursday'),
    (5, 'Friday'),
    (6, 'Saturday'),
]


class PhysioAvailability(models.Model):
    physio = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availability'
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_home = models.BooleanField(default=False)

    class Meta:
        unique_together = ['physio', 'day_of_week', 'is_home']
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        visit = 'Home' if self.is_home else 'Clinic'
        return f"{self.get_day_of_week_display()} {self.start_time}–{self.end_time} ({visit})"


class BookingRequest(models.Model):
    BOOKING_TYPE = [
        ('clinic', 'Clinic Visit'),
        ('home', 'Home Visit'),
    ]
    STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    physio = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='booking_requests'
    )
    patient_name = models.CharField(max_length=100)
    patient_contact = models.CharField(max_length=20)
    patient_email = models.EmailField(blank=True)
    condition = models.CharField(max_length=300)
    preferred_date = models.DateField()
    preferred_time = models.TimeField(null=True, blank=True)
    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPE, default='clinic')
    address = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.pk} {self.patient_name} → {self.physio.username} ({self.preferred_date})"

    def total_fee(self):
        try:
            profile = self.physio.physio_profile
            if self.booking_type == 'home':
                return profile.home_visit_fee + profile.platform_fee + profile.travel_cost
            return profile.consultation_fee + profile.platform_fee
        except PhysioProfile.DoesNotExist:
            return 0


class PhysioReview(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]

    physio = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    booking = models.ForeignKey(
        BookingRequest,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    reviewer_name = models.CharField(max_length=100)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reviewer_name} → {self.physio.username} ({self.rating}★)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            profile = self.physio.physio_profile
            approved = PhysioReview.objects.filter(physio=self.physio, is_approved=True)
            profile.total_reviews = approved.count()
            agg = approved.aggregate(a=Avg('rating'))
            profile.avg_rating = agg['a'] or 0
            profile.save(update_fields=['avg_rating', 'total_reviews'])
        except PhysioProfile.DoesNotExist:
            pass
