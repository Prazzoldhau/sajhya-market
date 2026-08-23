from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Public, non-account-gated pages worth indexing. Deliberately short --
    dashboards, checkout/cart, and anything behind login live under the
    '-acc/'/'-api/' prefixes disallowed in robots.txt and have no business
    in a sitemap anyway."""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return ['landing', 'marketplace', 'pharmacy', 'find-physio']

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    """One entry per in-stock, publicly listed product (Pharmacy excluded,
    same as every other public Marketplace query in marketplace_app.views)."""
    changefreq = 'weekly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        from marketplace_app.models import Product
        return Product.objects.filter(in_stock=True).exclude(category__name='Pharmacy')

    def location(self, obj):
        return reverse('product-detail', args=[obj.id])
