from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .models import LabTest, LabTestPanel

# Order/OrderItem live in marketplace_app -- reused rather than forking a
# fourth order system, same as Pharmacy's OrderItem.pharmacy_product. Lab
# Tests is otherwise a fully independent storefront/app: own top-level URL
# (/lab-tests/, mounted in sajhya_project.urls -- not nested under
# /marketplace/ the way Pharmacy is), own templates.
#
# No cart/checkout pages -- multi-select happens with plain checkboxes
# directly on the browse page (lab_tests.html), same one-page pick-then-
# submit pattern as exercise_app's "Prescribe Selected Exercises" (pick
# several, one submit, no per-item page hops). One POST here books
# everything checked as a single Order with one OrderItem per test/panel.
from marketplace_app.models import Order, OrderItem


def lab_tests(request):
    if request.method == 'POST':
        return _handle_bulk_booking(request)

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
    }
    return render(request, 'lab/lab_tests.html', context)


def _handle_bulk_booking(request):
    selected_keys = request.POST.getlist('items')
    customer_name = request.POST.get('customer_name', '').strip()
    customer_email = request.POST.get('customer_email', '').strip()
    customer_phone = request.POST.get('customer_phone', '').strip()
    delivery_address = request.POST.get('delivery_address', '').strip()
    notes = request.POST.get('notes', '').strip()

    if not selected_keys:
        messages.error(request, 'Select at least one test or panel first.')
        return redirect('lab-tests')

    if not all([customer_name, customer_email, customer_phone, delivery_address]):
        messages.error(request, 'Please fill in all required fields.')
        return redirect('lab-tests')

    items = []  # (lab_test_or_None, lab_panel_or_None, name, price)
    for key in selected_keys:
        item_type, _, item_id = key.partition('-')
        if item_type == 'test':
            obj = LabTest.objects.filter(id=item_id, is_active=True).first()
            if obj:
                items.append((obj, None, obj.name, obj.price))
        elif item_type == 'panel':
            obj = LabTestPanel.objects.filter(id=item_id, is_active=True).first()
            if obj:
                items.append((None, obj, obj.name, obj.price))

    if not items:
        messages.error(request, 'Your selected tests are no longer available -- please pick again.')
        return redirect('lab-tests')

    total = sum((price for _, _, _, price in items), Decimal('0.00'))

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
    for lab_test, lab_panel, name, price in items:
        OrderItem.objects.create(
            order=order,
            lab_test=lab_test,
            lab_panel=lab_panel,
            product_name=name,
            quantity=1,
            unit_price=price,
        )

    return redirect('lab-order-success', order_number=order.order_number)


def lab_test_detail(request, test_id):
    test = get_object_or_404(LabTest, id=test_id, is_active=True)
    return render(request, 'lab/lab_test_detail.html', {'test': test})


def lab_panel_detail(request, panel_id):
    panel = get_object_or_404(LabTestPanel, id=panel_id, is_active=True)
    return render(request, 'lab/lab_panel_detail.html', {'panel': panel})


def lab_order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'lab/lab_order_success.html', {'order': order})
