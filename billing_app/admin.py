from django.contrib import admin
from .models import BillingEntry


@admin.register(BillingEntry)
class BillingEntryAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'physio', 'entry_date', 'patient_name', 'service', 'rate', 'payment_mode')
    list_filter = ('payment_mode', 'entry_date', 'physio')
    search_fields = ('invoice_number', 'patient_name', 'contact_number', 'physio__username')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    date_hierarchy = 'entry_date'
