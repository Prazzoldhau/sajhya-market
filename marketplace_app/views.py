from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Category, Product, Order, OrderItem
from decimal import Decimal


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
    products = Product.objects.filter(in_stock=True).select_related('category')

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
