from django.contrib import admin
from .models import Referral


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        'referral_code', 'patient_name', 'referred_by',
        'referred_to', 'status', 'created_at',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['referral_code', 'patient_name', 'patient_diagnosis']
    readonly_fields = ['referral_code', 'created_at', 'updated_at']
