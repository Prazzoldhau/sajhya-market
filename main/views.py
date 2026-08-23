from django.shortcuts import render
from django.db.models import Count
from django.http import HttpResponse

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


def robots_txt(request):
    """Blocks the login-gated dashboard/account apps and transactional
    marketplace actions (cart, checkout, vendor tools, patient-specific
    picks) -- everything else public (marketplace listing/products,
    pharmacy, the find-a-physio directory and profiles) stays crawlable.
    Not a security boundary, just crawl-budget/index hygiene."""
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /acc/",
        "Disallow: /personal-acc/",
        "Disallow: /clinic-acc/",
        "Disallow: /enterprise-acc/",
        "Disallow: /physio-api/",
        "Disallow: /vendor-api/",
        "Disallow: /delivery/",
        "Disallow: /patient-app/",
        "Disallow: /visit-notes/",
        "Disallow: /upload-app/",
        "Disallow: /prescription-app/",
        "Disallow: /video-app/",
        "Disallow: /detail-app/",
        "Disallow: /exercise-app/",
        "Disallow: /summit/",
        "Disallow: /marketplace/patient/",
        "Disallow: /marketplace/cart/",
        "Disallow: /marketplace/checkout/",
        "Disallow: /marketplace/add-to-cart/",
        "Disallow: /marketplace/remove-from-cart/",
        "Disallow: /marketplace/update-cart/",
        "Disallow: /marketplace/order-success/",
        "Disallow: /marketplace/vendor/",
        "Disallow: /find-physio/manage/",
        "Disallow: /find-physio/booking/",
        "Disallow: /find-physio/*/book/",
        "",
        "Sitemap: https://sajhya.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")