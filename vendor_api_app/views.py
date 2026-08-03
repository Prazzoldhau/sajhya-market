import json
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from marketplace_app.models import Order

_STATUS_VALUES = [c[0] for c in Order.STATUS_CHOICES]


# ─── helpers ──────────────────────────────────────────────────────────────────

def _json_body(request):
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return {}


def _require_staff(request):
    """Return user if logged in and staff, else return an error JsonResponse."""
    if not request.user.is_authenticated:
        return None, JsonResponse({'error': 'Authentication required'}, status=401)
    if not request.user.is_staff:
        return None, JsonResponse({'error': 'Vendor staff access required'}, status=403)
    return request.user, None


def _order_source(order):
    """Orders are placed either by a physio (Order.user set) or a patient
    (physio_api_app/patient_app both create Orders without a user, patient
    orders use the synthetic '<patient_code>@sajhya.local' customer_email --
    see patient_app.views.patient_api_order)."""
    if order.user_id:
        return {'type': 'physio', 'name': order.user.get_full_name() or order.user.username}
    if order.customer_email.endswith('@sajhya.local'):
        return {'type': 'patient', 'name': order.customer_name, 'patient_code': order.customer_email.split('@')[0]}
    return {'type': 'guest', 'name': order.customer_name}


# ─── auth ─────────────────────────────────────────────────────────────────────

@ensure_csrf_cookie
def vendor_csrf(request):
    return JsonResponse({'detail': 'CSRF cookie set'})


@csrf_exempt
@require_http_methods(["POST"])
def vendor_login(request):
    data = _json_body(request)
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return JsonResponse({'error': 'Username and password required'}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'error': 'Invalid credentials'}, status=401)
    if not user.is_staff:
        return JsonResponse({'error': 'This account does not have vendor access'}, status=403)

    login(request, user)
    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
        }
    })


@require_http_methods(["POST"])
def vendor_logout(request):
    logout(request)
    return JsonResponse({'success': True})


def vendor_me(request):
    user, err = _require_staff(request)
    if err:
        return err
    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
        }
    })


# ─── orders ───────────────────────────────────────────────────────────────────

def order_list(request):
    user, err = _require_staff(request)
    if err:
        return err

    status_filter = request.GET.get('status', '').strip()
    orders = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')
    if status_filter in _STATUS_VALUES:
        orders = orders.filter(status=status_filter)

    all_orders = Order.objects.all()
    data = [
        {
            'order_number': o.order_number,
            'customer_name': o.customer_name,
            'customer_phone': o.customer_phone,
            'status': o.status,
            'total_amount': str(o.total_amount),
            'item_count': o.items.count(),
            'created_at': o.created_at.isoformat(),
            'source': _order_source(o),
        }
        for o in orders
    ]
    return JsonResponse({
        'orders': data,
        'status_choices': _STATUS_VALUES,
        'total_orders': all_orders.count(),
        'pending_count': all_orders.filter(status='pending').count(),
        'total_revenue': str(all_orders.aggregate(t=Sum('total_amount'))['t'] or 0),
    })


def order_detail(request, order_number):
    user, err = _require_staff(request)
    if err:
        return err

    order = get_object_or_404(Order, order_number=order_number)
    return JsonResponse({
        'order': {
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'customer_email': order.customer_email,
            'customer_phone': order.customer_phone,
            'delivery_address': order.delivery_address,
            'notes': order.notes,
            'status': order.status,
            'total_amount': str(order.total_amount),
            'created_at': order.created_at.isoformat(),
            'source': _order_source(order),
        },
        'items': [
            {
                'product_name': i.product_name,
                'quantity': i.quantity,
                'unit_price': str(i.unit_price),
                'total_price': str(i.total_price),
            }
            for i in order.items.all()
        ],
        'status_choices': _STATUS_VALUES,
    })


@require_http_methods(["POST"])
def order_update_status(request, order_number):
    user, err = _require_staff(request)
    if err:
        return err

    order = get_object_or_404(Order, order_number=order_number)
    data = _json_body(request)
    new_status = data.get('status', '').strip()
    if new_status not in _STATUS_VALUES:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    order.status = new_status
    order.save(update_fields=['status'])
    return JsonResponse({'success': True, 'status': order.status})
