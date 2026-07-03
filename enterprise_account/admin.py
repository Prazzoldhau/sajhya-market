from django.contrib import admin
from .models import Enterprise, Department, EnterpriseStaff, DepartmentClinic


@admin.register(Enterprise)
class EnterpriseAdmin(admin.ModelAdmin):
    list_display = ('enterprise_name', 'enterprise_code', 'phone', 'created_by', 'created_at')
    search_fields = ('enterprise_name', 'enterprise_code', 'registration_number')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('department_name', 'department_code', 'enterprise', 'hod', 'created_at')
    list_filter = ('enterprise',)
    search_fields = ('department_name', 'department_code')


@admin.register(EnterpriseStaff)
class EnterpriseStaffAdmin(admin.ModelAdmin):
    list_display = ('user', 'enterprise', 'department', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active', 'enterprise')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(DepartmentClinic)
class DepartmentClinicAdmin(admin.ModelAdmin):
    list_display = ('clinic', 'department', 'is_active', 'attached_by', 'attached_at')
    list_filter = ('is_active',)
    search_fields = ('clinic__clinic_name', 'department__department_name')
