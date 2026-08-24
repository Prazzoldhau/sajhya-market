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
        return ['landing', 'marketplace', 'pharmacy', 'lab-tests', 'find-physio', 'vacancy-list']

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    """One entry per in-stock Marketplace product -- Pharmacy has its own
    PharmacyProductSitemap below now that it's a separate catalog/table."""
    changefreq = 'weekly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        from marketplace_app.models import Product
        return Product.objects.filter(in_stock=True)

    def location(self, obj):
        return reverse('product-detail', args=[obj.id])


class PharmacyProductSitemap(Sitemap):
    """One entry per in-stock Pharmacy product."""
    changefreq = 'weekly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        from marketplace_app.models import PharmacyProduct
        return PharmacyProduct.objects.filter(in_stock=True)

    def location(self, obj):
        return reverse('pharmacy-product-detail', args=[obj.id])


class LabTestSitemap(Sitemap):
    """One entry per active individual lab test."""
    changefreq = 'monthly'
    priority = 0.5
    protocol = 'https'

    def items(self):
        from lab_app.models import LabTest
        return LabTest.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('lab-test-detail', args=[obj.id])


class LabTestPanelSitemap(Sitemap):
    """One entry per active lab test panel -- higher priority than individual
    tests since these are the bundles actively marketed."""
    changefreq = 'monthly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        from lab_app.models import LabTestPanel
        return LabTestPanel.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('lab-panel-detail', args=[obj.id])


class VacancySitemap(Sitemap):
    """One entry per open vacancy -- job listings are worth indexing on
    their own."""
    changefreq = 'daily'
    priority = 0.6
    protocol = 'https'

    def items(self):
        from careers_app.models import Vacancy
        return Vacancy.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('vacancy-detail', args=[obj.id])
