from django.contrib import admin
from .models import LabTest, LabTestRequest, LabTestRequestItem


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'turnaround_time', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name',)
    ordering = ('category', 'name')


class LabTestRequestItemInline(admin.TabularInline):
    model = LabTestRequestItem
    extra = 0
    readonly_fields = ('lab_test', 'test_name', 'price')
    can_delete = False


@admin.register(LabTestRequest)
class LabTestRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'patient', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('request_number', 'patient__patient_name', 'patient__patient_code')
    readonly_fields = ('request_number', 'patient', 'total_amount', 'created_at', 'updated_at')
    inlines = [LabTestRequestItemInline]
