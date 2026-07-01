from django.contrib import admin
from .models import Specialization, PhysioProfile, PhysioAvailability, BookingRequest, PhysioReview


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(PhysioProfile)
class PhysioProfileAdmin(admin.ModelAdmin):
    list_display = ['physio', 'location', 'consultation_fee', 'home_visit_fee', 'avg_rating', 'total_reviews', 'is_public']
    list_editable = ['is_public']
    list_filter = ['is_public', 'is_home_visit', 'is_clinic_visit']
    filter_horizontal = ['specializations']
    search_fields = ['physio__username', 'physio__first_name', 'physio__last_name', 'location']


@admin.register(PhysioAvailability)
class PhysioAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['physio', 'day_of_week', 'start_time', 'end_time', 'is_home']
    list_filter = ['day_of_week', 'is_home']


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'physio', 'preferred_date', 'booking_type', 'status', 'created_at']
    list_editable = ['status']
    list_filter = ['status', 'booking_type']
    search_fields = ['patient_name', 'patient_contact', 'physio__username']
    readonly_fields = ['created_at']


@admin.register(PhysioReview)
class PhysioReviewAdmin(admin.ModelAdmin):
    list_display = ['physio', 'reviewer_name', 'rating', 'is_approved', 'created_at']
    list_editable = ['is_approved']
    list_filter = ['is_approved', 'rating']
    search_fields = ['physio__username', 'reviewer_name']
