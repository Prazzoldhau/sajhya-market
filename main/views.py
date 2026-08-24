from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def landing_page(request):
    # Homepage marketplace teaser -- in-stock, non-Pharmacy, must have a real
    # photo (so the strip looks good) and a non-zero price (a "NPR 0" tile
    # looks broken -- e.g. unpriced Zuvara placeholder rows), capped to 8
    # (2 rows x 4 desktop). Randomized per request, same as the main
    # Marketplace grid (marketplace_app.views.marketplace) -- was previously
    # sorted best-seller/newest-first, which showed the same handful of
    # products on every visit.
    from marketplace_app.models import Product
    marketplace_preview = Product.objects.filter(in_stock=True)\
        .exclude(category__name='Pharmacy').exclude(image='')\
        .exclude(price=0)\
        .select_related('category')\
        .order_by('?')[:8]

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
        "Disallow: /marketplace/pharmacy/cart/",
        "Disallow: /marketplace/pharmacy/checkout/",
        "Disallow: /marketplace/pharmacy/add-to-cart/",
        "Disallow: /marketplace/pharmacy/remove-from-cart/",
        "Disallow: /marketplace/pharmacy/update-cart/",
        "Disallow: /marketplace/pharmacy/order-success/",
        "Disallow: /find-physio/manage/",
        "Disallow: /find-physio/booking/",
        "Disallow: /find-physio/*/book/",
        "",
        "Sitemap: https://sajhya.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")