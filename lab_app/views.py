from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .models import LabTest, LabTestPanel

# Order/OrderItem live in marketplace_app -- reused rather than forking a
# fourth order system, same as Pharmacy's OrderItem.pharmacy_product. Lab
# Tests is otherwise a fully independent storefront/app: own top-level URL
# (/lab-tests/, mounted in sajhya_project.urls -- not nested under
# /marketplace/ the way Pharmacy is), own templates.
#
# No cart here (unlike Marketplace/Pharmacy) -- each test/panel detail page
# has its own inline "Request This Test" booking form, same one-item,
# no-cart pattern as careers_app's vacancy apply form. One request in, one
# Order out, immediately.
from marketplace_app.models import Order, OrderItem


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
    }
    return render(request, 'lab/lab_tests.html', context)


def _book(request, *, lab_test=None, lab_panel=None):
    """Shared booking logic for a single test or panel -- creates one Order
    (order_type='lab_test') + one OrderItem and returns the redirect, or
    None if this wasn't a valid submit (caller re-renders the form)."""
    obj = lab_test or lab_panel
    customer_name = request.POST.get('customer_name', '').strip()
    customer_email = request.POST.get('customer_email', '').strip()
    customer_phone = request.POST.get('customer_phone', '').strip()
    delivery_address = request.POST.get('delivery_address', '').strip()
    notes = request.POST.get('notes', '').strip()

    if not all([customer_name, customer_email, customer_phone, delivery_address]):
        messages.error(request, 'Please fill in all required fields.')
        return None

    order = Order.objects.create(
        order_type='lab_test',
        user=request.user if request.user.is_authenticated else None,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        notes=notes,
        total_amount=obj.price,
    )
    OrderItem.objects.create(
        order=order,
        lab_test=lab_test,
        lab_panel=lab_panel,
        product_name=obj.name,
        quantity=1,
        unit_price=obj.price,
    )
    return redirect('lab-order-success', order_number=order.order_number)


def lab_test_detail(request, test_id):
    test = get_object_or_404(LabTest, id=test_id, is_active=True)
    if request.method == 'POST':
        result = _book(request, lab_test=test)
        if result:
            return result
    return render(request, 'lab/lab_test_detail.html', {'test': test})


def lab_panel_detail(request, panel_id):
    panel = get_object_or_404(LabTestPanel, id=panel_id, is_active=True)
    if request.method == 'POST':
        result = _book(request, lab_panel=panel)
        if result:
            return result
    return render(request, 'lab/lab_panel_detail.html', {'panel': panel})


def lab_order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'lab/lab_order_success.html', {'order': order})
