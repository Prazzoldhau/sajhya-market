from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.template.loader import render_to_string
from django.db.models import Sum, Count
from .models import Category, Product, PharmacyProduct, Order, OrderItem, DiagnosisProductMap, PatientProductRecommendation
from decimal import Decimal
from functools import wraps
import random


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


# Pharmacy is a fully separate catalog/cart from Marketplace now (own
# PharmacyProduct table, own session key) -- see the "database... different
# than of marketplace" ask this shipped for. Same session-cart pattern as
# Marketplace, just under its own key so the two never collide.
def _get_pharmacy_cart(request):
    return request.session.get('pharmacy_cart', {})


def _save_pharmacy_cart(request, cart):
    request.session['pharmacy_cart'] = cart
    request.session.modified = True


def get_pharmacy_cart_count(request):
    return sum(item['quantity'] for item in _get_pharmacy_cart(request).values())


# Lab test cart is shaped differently from the product carts above: a test
# or panel is either selected or not (no "3x CBC"), so there's no quantity
# field at all -- each cart line is keyed 'test-<id>' or 'panel-<id>' and
# adding an already-present item is a no-op rather than incrementing.
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


def _get_shuffled_products(request, products, filter_key, session_key, reshuffle):
    """Random order for a product grid, re-rolled on every fresh page load
    but held stable (in the session) across the infinite-scroll AJAX batches
    of that same visit -- otherwise each batch request would get its own
    fresh shuffle and products would repeat or get skipped as you scroll.
    session_key is namespaced per catalog (marketplace vs pharmacy) so the
    two never clobber each other's shuffle state."""
    stored = request.session.get(session_key)

    if reshuffle or not stored or stored.get('key') != filter_key:
        ids = list(products.values_list('id', flat=True))
        random.shuffle(ids)
        stored = {'key': filter_key, 'ids': ids}
        request.session[session_key] = stored
        request.session.modified = True

    by_id = {p.id: p for p in products}
    return [by_id[pid] for pid in stored['ids'] if pid in by_id]


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
            'image': item.get('image', ''),
            'item_total': item_total,
        })
    return lines, total


# Same shape as _build_cart_lines -- kept as a separate function (not a
# shared helper with a "which cart" flag) since the two carts' items key off
# unrelated models (Product vs PharmacyProduct) and are never meant to mix.
def _build_pharmacy_cart_lines(cart):
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
            'image': item.get('image', ''),
            'item_total': item_total,
        })
    return lines, total


def marketplace(request):
    # Pharmacy is a separate section (see `pharmacy` view below) -- never
    # listed or searchable from the general Marketplace page.
    categories = Category.objects.exclude(name='Pharmacy')
    products = Product.objects.filter(in_stock=True).exclude(category__name='Pharmacy').select_related('category')

    category_id = request.GET.get('category', '').strip()
    if category_id:
        products = products.filter(category_id=category_id)

    search = request.GET.get('search', '').strip()
    condition_matches = None
    condition_label = ''
    if search:
        products = products.filter(name__icontains=search)
        # A patient searching "knee pain" won't match any product *name*, but
        # might match a condition we already curate products for (physios
        # build this list via DiagnosisProductMap) -- surface that as a
        # distinct "Recommended for X" row, most-purchased first, same
        # proxy for "most effective" the rest of the catalog already uses
        # since there's no ratings/reviews data to rank on.
        condition_products, condition_label = get_recommended_for_diagnosis(search)
        if condition_label:
            condition_matches = condition_products.select_related('category')\
                .annotate(order_count=Count('orderitem'))\
                .order_by('-order_count', 'name')[:8]

    featured = Product.objects.filter(is_featured=True, in_stock=True).exclude(category__name='Pharmacy').select_related('category')[:4]

    # Shuffled, not alphabetical/best-seller order -- reshuffled on every
    # fresh visit to this filter combo (category+search), but held stable in
    # the session across infinite-scroll batches of that same visit, since
    # re-randomizing on every AJAX page fetch would repeat/skip products as
    # you scroll. _get_shuffled_products below does the actual reorder.
    page_param = request.GET.get('page')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    ordered_products = _get_shuffled_products(
        request, products, filter_key=f'{category_id}|{search}', session_key='marketplace_shuffle',
        reshuffle=not is_ajax and page_param in (None, '', '1'),
    )

    # 259+ products rendered in one page was slow and image-heavy -- page it.
    # The page renders batch 1 server-side; the infinite-scroll JS on
    # marketplace.html re-requests this same view for batch 2+ with
    # X-Requested-With set and just wants the new cards back, not a full page.
    paginator = Paginator(ordered_products, 24)
    page_obj = paginator.get_page(page_param)

    if is_ajax:
        html = render_to_string('marketplace/_product_cards.html', {'products': page_obj}, request=request)
        return JsonResponse({
            'html': html,
            'has_next': page_obj.has_next(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        })

    context = {
        'categories': categories,
        'products': page_obj,
        'page_obj': page_obj,
        'featured': featured,
        'condition_matches': condition_matches,
        'condition_label': condition_label,
        'selected_category': category_id,
        'search': search,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'marketplace/marketplace.html', context)


def pharmacy(request):
    products = PharmacyProduct.objects.filter(in_stock=True)

    search = request.GET.get('search', '').strip()
    if search:
        products = products.filter(name__icontains=search)

    featured = PharmacyProduct.objects.filter(is_featured=True, in_stock=True)[:4]

    # Same random-order + infinite-scroll treatment as the Marketplace grid
    # (marketplace() above) -- see _get_shuffled_products for why the
    # shuffle is session-cached rather than re-rolled on every AJAX batch.
    page_param = request.GET.get('page')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    ordered_products = _get_shuffled_products(
        request, products, filter_key=search, session_key='pharmacy_shuffle',
        reshuffle=not is_ajax and page_param in (None, '', '1'),
    )

    paginator = Paginator(ordered_products, 24)
    page_obj = paginator.get_page(page_param)

    if is_ajax:
        html = render_to_string('marketplace/_pharmacy_product_cards.html', {'products': page_obj}, request=request)
        return JsonResponse({
            'html': html,
            'has_next': page_obj.has_next(),
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        })

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'featured': featured,
        'search': search,
        'cart_count': get_pharmacy_cart_count(request),
    }
    return render(request, 'marketplace/pharmacy.html', context)


def pharmacy_product_detail(request, product_id):
    product = get_object_or_404(PharmacyProduct, id=product_id)
    related = PharmacyProduct.objects.filter(in_stock=True).exclude(id=product_id).order_by('?')[:4]

    context = {
        'product': product,
        'related': related,
        'cart_count': get_pharmacy_cart_count(request),
    }
    return render(request, 'marketplace/pharmacy_product_detail.html', context)


def pharmacy_add_to_cart(request, product_id):
    product = get_object_or_404(PharmacyProduct, id=product_id)
    cart = _get_pharmacy_cart(request)
    pid = str(product_id)

    if pid in cart:
        cart[pid]['quantity'] += 1
    else:
        cart[pid] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': 1,
            'unit': product.unit,
            'category': product.category,
            'image': product.image,
        }

    _save_pharmacy_cart(request, cart)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'cart_count': get_pharmacy_cart_count(request)})

    messages.success(request, f'"{product.name}" added to cart!')
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or 'pharmacy'
    return redirect(next_url)


def pharmacy_remove_from_cart(request, product_id):
    cart = _get_pharmacy_cart(request)
    pid = str(product_id)
    if pid in cart:
        del cart[pid]
        _save_pharmacy_cart(request, cart)
        messages.success(request, 'Item removed from cart.')
    return redirect('pharmacy-view-cart')


def pharmacy_update_cart(request, product_id):
    if request.method != 'POST':
        return redirect('pharmacy-view-cart')
    cart = _get_pharmacy_cart(request)
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

    _save_pharmacy_cart(request, cart)
    return redirect('pharmacy-view-cart')


def pharmacy_view_cart(request):
    cart = _get_pharmacy_cart(request)
    cart_items, total = _build_pharmacy_cart_lines(cart)
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': get_pharmacy_cart_count(request),
    }
    return render(request, 'marketplace/pharmacy_cart.html', context)


def pharmacy_checkout(request):
    cart = _get_pharmacy_cart(request)

    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('pharmacy')

    cart_items, total = _build_pharmacy_cart_lines(cart)

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
                order_type='pharmacy',
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
                    pharmacy_product = PharmacyProduct.objects.get(id=item['product_id'])
                except PharmacyProduct.DoesNotExist:
                    pharmacy_product = None

                OrderItem.objects.create(
                    order=order,
                    pharmacy_product=pharmacy_product,
                    product_name=item['name'],
                    quantity=item['quantity'],
                    unit_price=item['price'],
                )

            _save_pharmacy_cart(request, {})
            return redirect('pharmacy-order-success', order_number=order.order_number)

    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': 0,
    }
    return render(request, 'marketplace/pharmacy_checkout.html', context)


def pharmacy_order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'marketplace/pharmacy_order_success.html', {'order': order})


# Lab Tests -- third storefront alongside Marketplace/Pharmacy, same
# checkout/Order infrastructure. LabTest/LabTestPanel live in lab_app (not
# imported at module level to avoid a hard marketplace_app <-> lab_app
# import-time coupling, same reasoning as the personal_account imports
# further down this file).

def lab_tests(request):
    from lab_app.models import LabTest, LabTestPanel

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
    return render(request, 'marketplace/lab_tests.html', context)


def lab_test_detail(request, test_id):
    from lab_app.models import LabTest
    test = get_object_or_404(LabTest, id=test_id, is_active=True)
    context = {'test': test, 'cart_count': get_lab_cart_count(request)}
    return render(request, 'marketplace/lab_test_detail.html', context)


def lab_panel_detail(request, panel_id):
    from lab_app.models import LabTestPanel
    panel = get_object_or_404(LabTestPanel, id=panel_id, is_active=True)
    context = {'panel': panel, 'cart_count': get_lab_cart_count(request)}
    return render(request, 'marketplace/lab_panel_detail.html', context)


def lab_add_to_cart(request, item_type, item_id):
    from lab_app.models import LabTest, LabTestPanel
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
    return render(request, 'marketplace/lab_cart.html', context)


def lab_checkout(request):
    from lab_app.models import LabTest, LabTestPanel
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
    return render(request, 'marketplace/lab_checkout.html', context)


def lab_order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'marketplace/lab_order_success.html', {'order': order})


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
            'image': product.image,
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
    """Return Product queryset matching the patient's diagnosis keywords.

    Excludes Pharmacy the same as every other Marketplace listing query --
    a DiagnosisProductMap could in principle map a keyword to a Pharmacy
    product, which would otherwise leak it into the general Marketplace's
    "Recommended for X" row. Pharmacy stays reachable only via its own tab."""
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
    return Product.objects.filter(id__in=matched_pks, in_stock=True).exclude(category__name='Pharmacy').distinct(), matched_label


def patient_marketplace(request, patient_id):
    from personal_account.models import AddPatient
    patient = get_object_or_404(AddPatient, id=patient_id)

    # Manual recs from physio (shown first) -- excludes Pharmacy same as
    # every other Marketplace query; nothing stops a physio from picking a
    # Pharmacy product here otherwise, which would leak it out of its tab.
    manual_recs = (
        PatientProductRecommendation.objects.filter(patient=patient)
        .exclude(product__category__name='Pharmacy')
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
        .exclude(category__name='Pharmacy')
        .select_related('category')
        .annotate(order_count=Count('orderitem'))
        .order_by('-is_featured', '-order_count', 'name')
    )

    # IDs the physio has already recommended (for toggle state on cards)
    is_physio = request.user.is_authenticated
    categories = Category.objects.exclude(name='Pharmacy')
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
    # Excludes Pharmacy -- this adds straight to the cart, so a Pharmacy
    # item here wouldn't just be a display leak, it'd actually bypass the
    # Pharmacy tab and land in the general cart.
    recs = PatientProductRecommendation.objects.filter(patient=patient).exclude(product__category__name='Pharmacy').select_related('product', 'product__category')
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
                'image': p.image,
            }
    _save_cart(request, cart)
    return redirect('view-cart')
