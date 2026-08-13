from django.contrib import admin
from django.utils import timezone

from .models import Zone, Rider, Delivery


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ['rider_code', 'user', 'vehicle_type', 'current_zone', 'status', 'created_at']
    list_filter = ['status', 'vehicle_type', 'current_zone']
    search_fields = ['rider_code', 'user__username', 'user__phone']
    readonly_fields = ['rider_code', 'created_at', 'updated_at']


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    """This is the Stage-1 dispatch board: staff assign a rider and a drop
    zone straight from the change list. A custom dispatch UI is deferred
    until real usage shows admin isn't enough (see plan)."""
    list_display = [
        'order', 'rider', 'pickup_zone', 'drop_zone', 'status',
        'cod_amount', 'cod_collected', 'created_at',
    ]
    list_display_links = ['order']
    list_editable = ['rider', 'drop_zone']
    list_filter = ['status', 'pickup_zone', 'drop_zone', 'cod_collected']
    search_fields = ['order__order_number', 'order__customer_name', 'order__customer_phone']
    readonly_fields = ['order', 'created_at']
    autocomplete_fields = ['rider']

    def save_model(self, request, obj, form, change):
        # Staff shouldn't have to remember two separate edits: assigning a
        # rider to a still-unassigned delivery should read as "assigned".
        if obj.rider and obj.status == 'unassigned':
            obj.status = 'assigned'
            obj.assigned_at = timezone.now()
        super().save_model(request, obj, form, change)
