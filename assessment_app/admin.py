from django.contrib import admin
from .models import SpecialTestReference, RegionalAssessment


@admin.register(SpecialTestReference)
class SpecialTestReferenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'purpose', 'order', 'is_active')
    list_filter = ('region', 'is_active')
    search_fields = ('name', 'purpose')
    ordering = ('region', 'order', 'name')


@admin.register(RegionalAssessment)
class RegionalAssessmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'region', 'created_by', 'created_at')
    list_filter = ('region',)
    search_fields = ('patient__patient_name', 'patient__patient_code')
    ordering = ('-created_at',)
