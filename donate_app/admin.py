from django.contrib import admin
from .models import DonatableCategory, DonationPledge


@admin.register(DonatableCategory)
class DonatableCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'image', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    search_fields = ('name',)


@admin.register(DonationPledge)
class DonationPledgeAdmin(admin.ModelAdmin):
    list_display = ('pledge_number', 'donor_name', 'phone_number', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    list_editable = ('status',)
    search_fields = ('pledge_number', 'donor_name', 'phone_number', 'address')
    readonly_fields = ('pledge_number', 'created_at')
    filter_horizontal = ('items',)
