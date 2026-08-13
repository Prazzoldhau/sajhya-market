from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Delivery

_DELIVERY_STATUS_VALUES = ['picked_up', 'in_transit', 'delivered', 'failed']

# Delivery.status -> Order.status, mirroring marketplace_app.Order.STATUS_CHOICES
# so the existing vendor_orders/vendor_order_detail views stay accurate with
# no changes there. 'failed' has no clean Order-status equivalent, so it's
# left for staff to resolve manually via the normal order status dropdown.
_ORDER_STATUS_SYNC = {
    'picked_up': 'shipped',
    'in_transit': 'shipped',
    'delivered': 'delivered',
}


def rider_required(view_func):
    """Mirrors marketplace_app.views.staff_required."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/acc/login/?next={request.path}")
        if request.user.user_type != 'rider' or not hasattr(request.user, 'rider_profile'):
            messages.error(request, 'Rider account required.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


@rider_required
def rider_dashboard(request):
    rider = request.user.rider_profile
    deliveries = (
        Delivery.objects.filter(rider=rider)
        .exclude(status__in=['delivered', 'failed'])
        .select_related('order', 'pickup_zone', 'drop_zone')
        .order_by('status', 'assigned_at')
    )
    context = {
        'rider': rider,
        'deliveries': deliveries,
    }
    return render(request, 'delivery_app/rider-dashboard.html', context)


@rider_required
def toggle_availability(request):
    if request.method == 'POST':
        rider = request.user.rider_profile
        rider.status = 'offline' if rider.status != 'offline' else 'available'
        rider.save(update_fields=['status', 'updated_at'])
    return redirect('rider-dashboard')


@rider_required
def update_delivery_status(request, delivery_id):
    rider = request.user.rider_profile
    delivery = get_object_or_404(Delivery, id=delivery_id, rider=rider)

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        if new_status in _DELIVERY_STATUS_VALUES:
            now = timezone.now()
            delivery.status = new_status
            if new_status == 'picked_up':
                delivery.picked_up_at = now
            elif new_status == 'delivered':
                delivery.delivered_at = now
                if request.POST.get('cod_collected') == 'on':
                    delivery.cod_collected = True
                    delivery.cod_collected_at = now
            elif new_status == 'failed':
                delivery.failure_reason = request.POST.get('failure_reason', '').strip()
            delivery.save()

            order_status = _ORDER_STATUS_SYNC.get(new_status)
            if order_status:
                delivery.order.status = order_status
                delivery.order.save(update_fields=['status'])

            messages.success(request, f'Delivery marked as "{delivery.get_status_display()}".')
        else:
            messages.error(request, 'Invalid status.')

    return redirect('rider-dashboard')
