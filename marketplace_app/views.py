from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.db.models import Sum, Count
from .models import Category, Product, Order, OrderItem, DiagnosisProductMap, PatientProductRecommendation
from decimal import Decimal
from functools import wraps


def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/acc/login/?next={request.path}")
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


_STATUS_VALUES = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']


def _get_cart(request):
    return request.session.get('marketplace_cart', {})


def _save_cart(request, cart):
    request.session['marketplace_cart'] = cart
    request.session.modified = True


def get_cart_count(request):
    return sum(item['quantity'] for item in _get_cart(request).values())


def _build_cart_lines(cart):
    lines = []
    total = Decimal('0.00')
    for pid, item in cart.items():
        item_total = Decimal(str(item['price'])) * item['quantity']
        total += item_total
        lines.append({
            'product_id': int(pid),
            'name': item['name'],
            'price': Decimal(str(item['price'])),
            'quantity': item['quantity'],
            'unit': item.get('unit', ''),
            'category': item.get('category', ''),
            'item_total': item_total,
        })
    return lines, total


def marketplace(request):
    categories = Category.objects.all()
    products = Product.objects.filter(in_stock=True).select_related('category')\
        .annotate(order_count=Count('orderitem'))\
        .order_by('-is_featured', '-order_count', 'name')

    category_id = request.GET.get('category', '').strip()
    if category_id:
        products = products.filter(category_id=category_id)

    search = request.GET.get('search', '').strip()
    if search:
        products = products.filter(name__icontains=search)

    featured = Product.objects.filter(is_featured=True, in_stock=True).select_related('category')[:4]

    context = {
        'categories': categories,
        'products': products,
        'featured': featured,
        'selected_category': category_id,
        'search': search,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'marketplace/marketplace.html', context)


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    related = Product.objects.filter(
        category=product.category, in_stock=True
    ).exclude(id=product_id).select_related('category')[:4]

    context = {
        'product': product,
        'related': related,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'marketplace/product_detail.html', context)


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = _get_cart(request)
    pid = str(product_id)

    if pid in cart:
        cart[pid]['quantity'] += 1
    else:
        cart[pid] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': 1,
            'unit': product.unit,
            'category': product.category.name if product.category else '',
        }

    _save_cart(request, cart)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'cart_count': get_cart_count(request)})

    messages.success(request, f'"{product.name}" added to cart!')
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or 'marketplace'
    return redirect(next_url)


def remove_from_cart(request, product_id):
    cart = _get_cart(request)
    pid = str(product_id)
    if pid in cart:
        del cart[pid]
        _save_cart(request, cart)
        messages.success(request, 'Item removed from cart.')
    return redirect('view-cart')


def update_cart(request, product_id):
    if request.method != 'POST':
        return redirect('view-cart')
    cart = _get_cart(request)
    pid = str(product_id)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if pid in cart:
        if quantity <= 0:
            del cart[pid]
        else:
            cart[pid]['quantity'] = quantity

    _save_cart(request, cart)
    return redirect('view-cart')


def view_cart(request):
    cart = _get_cart(request)
    cart_items, total = _build_cart_lines(cart)
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'marketplace/cart.html', context)


def checkout(request):
    cart = _get_cart(request)

    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('marketplace')

    cart_items, total = _build_cart_lines(cart)

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '').strip()
        customer_email = request.POST.get('customer_email', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        delivery_address = request.POST.get('delivery_address', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not all([customer_name, customer_email, customer_phone, delivery_address]):
            messages.error(request, 'Please fill in all required fields.')
        else:
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                delivery_address=delivery_address,
                notes=notes,
                total_amount=total,
            )

            for item in cart_items:
                try:
                    product = Product.objects.get(id=item['product_id'])
                except Product.DoesNotExist:
                    product = None

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=item['name'],
                    quantity=item['quantity'],
                    unit_price=item['price'],
                )

            _save_cart(request, {})
            return redirect('order-success', order_number=order.order_number)

    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': 0,
    }
    return render(request, 'marketplace/checkout.html', context)


def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'marketplace/order_success.html', {'order': order})


@staff_required
def vendor_orders(request):
    status_filter = request.GET.get('status', '').strip()
    orders = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')
    if status_filter in _STATUS_VALUES:
        orders = orders.filter(status=status_filter)

    all_orders = Order.objects.all()
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'status_choices': _STATUS_VALUES,
        'total_orders': all_orders.count(),
        'pending_count': all_orders.filter(status='pending').count(),
        'total_revenue': all_orders.aggregate(t=Sum('total_amount'))['t'] or 0,
    }
    return render(request, 'marketplace/vendor_orders.html', context)


@staff_required
def vendor_order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        if new_status in _STATUS_VALUES:
            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, f'Status updated to "{order.get_status_display()}".')
        else:
            messages.error(request, 'Invalid status.')
        return redirect('vendor-order-detail', order_number=order.order_number)

    context = {
        'order': order,
        'items': order.items.all(),
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'marketplace/vendor_order_detail.html', context)


def get_recommended_for_diagnosis(diagnosis_text):
    """Return Product queryset matching the patient's diagnosis keywords."""
    if not diagnosis_text:
        return Product.objects.none()
    diagnosis_lower = diagnosis_text.lower()
    matched_pks = []
    matched_label = ''
    for dmap in DiagnosisProductMap.objects.prefetch_related('products'):
        if dmap.keyword.lower() in diagnosis_lower:
            matched_pks.extend(dmap.products.filter(in_stock=True).values_list('id', flat=True))
            if not matched_label:
                matched_label = dmap.label or dmap.keyword.title()
    return Product.objects.filter(id__in=matched_pks, in_stock=True).distinct(), matched_label


def patient_marketplace(request, patient_id):
    from personal_account.models import AddPatient
    patient = get_object_or_404(AddPatient, id=patient_id)

    # Manual recs from physio (shown first)
    manual_recs = (
        PatientProductRecommendation.objects.filter(patient=patient)
        .select_related('product', 'product__category')
    )
    manual_ids = list(manual_recs.values_list('product_id', flat=True))

    # Auto recs from diagnosis (shown second, exclude manually added ones)
    auto_recommended, matched_label = get_recommended_for_diagnosis(patient.patient_diagnosis)
    auto_recommended = auto_recommended.exclude(id__in=manual_ids)
    auto_ids = list(auto_recommended.values_list('id', flat=True))

    excluded_ids = manual_ids + auto_ids

    other_products = (
        Product.objects.filter(in_stock=True)
        .exclude(id__in=excluded_ids)
        .select_related('category')
        .annotate(order_count=Count('orderitem'))
        .order_by('-is_featured', '-order_count', 'name')
    )

    # IDs the physio has already recommended (for toggle state on cards)
    is_physio = request.user.is_authenticated
    categories = Category.objects.all()
    context = {
        'patient': patient,
        'manual_recs': manual_recs,
        'manual_ids': manual_ids,
        'auto_recommended': auto_recommended.select_related('category'),
        'matched_label': matched_label,
        'other_products': other_products,
        'categories': categories,
        'cart_count': get_cart_count(request),
        'is_physio': is_physio,
    }
    return render(request, 'marketplace/patient-marketplace.html', context)


def add_patient_recommendation(request, patient_id, product_id):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    from personal_account.models import AddPatient
    patient = get_object_or_404(AddPatient, id=patient_id)
    product = get_object_or_404(Product, id=product_id)
    note = request.POST.get('note', '')
    rec, created = PatientProductRecommendation.objects.get_or_create(
        patient=patient, product=product,
        defaults={'recommended_by': request.user if request.user.is_authenticated else None, 'note': note}
    )
    if not created and note:
        rec.note = note
        rec.save(update_fields=['note'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'created': created, 'rec_id': rec.id})
    return redirect(request.META.get('HTTP_REFERER', 'patient-marketplace'))


def remove_patient_recommendation(request, rec_id):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    rec = get_object_or_404(PatientProductRecommendation, id=rec_id)
    rec.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect(request.META.get('HTTP_REFERER', 'patient-marketplace'))


def add_picks_to_cart(request, patient_id):
    """Add all physio-picked products for a patient into the current session cart."""
    from personal_account.models import AddPatient
    patient = get_object_or_404(AddPatient, id=patient_id)
    recs = PatientProductRecommendation.objects.filter(patient=patient).select_related('product', 'product__category')
    cart = _get_cart(request)
    for rec in recs:
        p = rec.product
        if not p.in_stock:
            continue
        pid = str(p.id)
        if pid not in cart:
            cart[pid] = {
                'name': p.name,
                'price': str(p.price),
                'quantity': 1,
                'unit': p.unit,
                'category': p.category.name if p.category else '',
            }
    _save_cart(request, cart)
    return redirect('view-cart')
