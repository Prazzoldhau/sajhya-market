from decimal import Decimal

from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import LabTest, LabTestPanel

# Order/OrderItem live in marketplace_app -- reused rather than forking a
# fourth order system, same as Pharmacy's OrderItem.pharmacy_product. Lab
# Tests is otherwise a fully independent storefront/app: own top-level URL
# (/lab-tests/, mounted in sajhya_project.urls -- not nested under
# /marketplace/ the way Pharmacy is), own templates, own session cart.
from marketplace_app.models import Order, OrderItem


# Lab test cart is shaped differently from the product carts in
# marketplace_app.views: a test or panel is either selected or not (no
# "3x CBC"), so there's no quantity field at all -- each cart line is keyed
# 'test-<id>' or 'panel-<id>' and adding an already-present item is a no-op
# rather than incrementing.
def _get_lab_cart(request):
    return request.session.get('lab_cart', {})


def _save_lab_cart(request, cart):
    request.session['lab_cart'] = cart
    request.session.modified = True


def get_lab_cart_count(request):
    return len(_get_lab_cart(request))


def _build_lab_cart_lines(cart):
    lines = []
    total = Decimal('0.00')
    for key, item in cart.items():
        price = Decimal(str(item['price']))
        total += price
        lines.append({
            'key': key,
            'type': item['type'],
            'id': item['id'],
            'name': item['name'],
            'price': price,
        })
    return lines, total


def lab_tests(request):
    search = request.GET.get('search', '').strip()

    panels = LabTestPanel.objects.filter(is_active=True).prefetch_related('tests').order_by('-is_featured', 'name')
    tests = LabTest.objects.filter(is_active=True)
    if search:
        panels = panels.filter(name__icontains=search)
        tests = tests.filter(name__icontains=search)

    # Grouped by category (Hematology, Biochemistry, ...) rather than
    # shuffled like the Marketplace/Pharmacy grids -- picking lab tests is a
    # deliberate checklist exercise, not browsing-for-discovery, so grouping
    # by what they're testing for is more useful than random surfacing.
    category_labels = dict(LabTest.CATEGORY_CHOICES)
    grouped = {}
    for t in tests.order_by('category', 'name'):
        grouped.setdefault(t.category, []).append(t)
    categorized_tests = [(category_labels.get(cat, cat), items) for cat, items in grouped.items()]

    context = {
        'panels': panels,
        'categorized_tests': categorized_tests,
        'search': search,
        'cart_count': get_lab_cart_count(request),
    }
    return render(request, 'lab/lab_tests.html', context)


def lab_test_detail(request, test_id):
    test = get_object_or_404(LabTest, id=test_id, is_active=True)
    context = {'test': test, 'cart_count': get_lab_cart_count(request)}
    return render(request, 'lab/lab_test_detail.html', context)


def lab_panel_detail(request, panel_id):
    panel = get_object_or_404(LabTestPanel, id=panel_id, is_active=True)
    context = {'panel': panel, 'cart_count': get_lab_cart_count(request)}
    return render(request, 'lab/lab_panel_detail.html', context)


def lab_add_to_cart(request, item_type, item_id):
    if item_type == 'test':
        obj = get_object_or_404(LabTest, id=item_id, is_active=True)
    elif item_type == 'panel':
        obj = get_object_or_404(LabTestPanel, id=item_id, is_active=True)
    else:
        raise Http404('Unknown lab cart item type.')

    cart = _get_lab_cart(request)
    key = f'{item_type}-{item_id}'
    cart[key] = {'type': item_type, 'id': item_id, 'name': obj.name, 'price': str(obj.price)}
    _save_lab_cart(request, cart)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'cart_count': get_lab_cart_count(request)})

    messages.success(request, f'"{obj.name}" added to your lab test cart!')
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or 'lab-tests'
    return redirect(next_url)


def lab_remove_from_cart(request, item_type, item_id):
    cart = _get_lab_cart(request)
    key = f'{item_type}-{item_id}'
    if key in cart:
        del cart[key]
        _save_lab_cart(request, cart)
        messages.success(request, 'Removed from your lab test cart.')
    return redirect('lab-view-cart')


def lab_view_cart(request):
    cart = _get_lab_cart(request)
    cart_items, total = _build_lab_cart_lines(cart)
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': get_lab_cart_count(request),
    }
    return render(request, 'lab/lab_cart.html', context)


def lab_checkout(request):
    cart = _get_lab_cart(request)

    if not cart:
        messages.warning(request, 'Your lab test cart is empty.')
        return redirect('lab-tests')

    cart_items, total = _build_lab_cart_lines(cart)

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
                order_type='lab_test',
                user=request.user if request.user.is_authenticated else None,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                delivery_address=delivery_address,
                notes=notes,
                total_amount=total,
            )

            for item in cart_items:
                lab_test = None
                lab_panel = None
                if item['type'] == 'test':
                    lab_test = LabTest.objects.filter(id=item['id']).first()
                else:
                    lab_panel = LabTestPanel.objects.filter(id=item['id']).first()

                OrderItem.objects.create(
                    order=order,
                    lab_test=lab_test,
                    lab_panel=lab_panel,
                    product_name=item['name'],
                    quantity=1,
                    unit_price=item['price'],
                )

            _save_lab_cart(request, {})
            return redirect('lab-order-success', order_number=order.order_number)

    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': 0,
    }
    return render(request, 'lab/lab_checkout.html', context)


def lab_order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'lab/lab_order_success.html', {'order': order})
