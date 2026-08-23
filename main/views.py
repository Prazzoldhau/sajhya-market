from django.shortcuts import render
from django.db.models import Count

# Create your views here.
def landing_page(request):
    # Homepage marketplace teaser -- same in-stock/non-Pharmacy/best-first
    # ordering as the real Marketplace grid (marketplace_app.views.marketplace),
    # but only products with a real photo so the strip looks good, and capped
    # to 8 (2 rows x 4 desktop) since this is a teaser, not the full catalog.
    from marketplace_app.models import Product
    # Excludes price=0 placeholder rows (e.g. unpriced Zuvara SKUs) -- a "NPR 0"
    # tile looks broken on a marketing teaser. Falls back to newest-first
    # rather than alphabetical once order_count ties out, since recently
    # imported catalogs (UM Orthotics, Slurrp Farm) have the real product
    # photos -- mark more products `is_featured` in admin to hand-curate this.
    marketplace_preview = Product.objects.filter(in_stock=True)\
        .exclude(category__name='Pharmacy').exclude(image='')\
        .exclude(price=0)\
        .select_related('category')\
        .annotate(order_count=Count('orderitem'))\
        .order_by('-is_featured', '-order_count', '-id')[:8]

    return render(request, 'index.html', {'marketplace_preview': marketplace_preview})