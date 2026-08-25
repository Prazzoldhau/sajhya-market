from django.contrib import admin
from .models import LabTest, LabTestPanel, LabTestRequest, LabTestRequestItem


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'turnaround_time', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name',)
    ordering = ('category', 'name')


@admin.register(LabTestPanel)
class LabTestPanelAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'a_la_carte_total', 'savings', 'is_featured', 'is_active')
    list_filter = ('is_featured', 'is_active')
    search_fields = ('name',)
    filter_horizontal = ('tests',)


class LabTestRequestItemInline(admin.TabularInline):
    model = LabTestRequestItem
    extra = 0
    readonly_fields = ('lab_test', 'lab_panel', 'test_name', 'price')
    can_delete = False


@admin.register(LabTestRequest)
class LabTestRequestAdmin(admin.ModelAdmin):
    # patient is set for mobile-app bookings, customer_name/customer_phone
    # for website bookings (the two ways a request gets created -- see
    # LabTestRequest's docstring) -- both shown so either kind is easy to
    # spot in one list.
    list_display = ('request_number', 'patient', 'customer_name', 'customer_phone', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    list_editable = ('status',)
    search_fields = ('request_number', 'patient__patient_name', 'patient__patient_code', 'customer_name', 'customer_phone', 'customer_email')
    readonly_fields = ('request_number', 'patient', 'total_amount', 'created_at', 'updated_at')
    inlines = [LabTestRequestItemInline]
