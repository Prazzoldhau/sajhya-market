from django.contrib import admin
from .models import ActivationCard


@admin.register(ActivationCard)
class ActivationCardAdmin(admin.ModelAdmin):
    list_display = ('code', 'duration_days', 'is_used', 'used_by', 'used_at', 'created_at')
    list_filter = ('is_used', 'duration_days')
    search_fields = ('code', 'used_by__patient_code', 'used_by__patient_name')
    readonly_fields = ('code', 'qr_code', 'used_by', 'used_at', 'created_at')
