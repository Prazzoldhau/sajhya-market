"""
Seeds PharmacyProduct from a supplier purchase record (a spreadsheet of
medicine name / batch-or-strength / form / quantity purchased / total cost
paid to the supplier -- e.g. "Gabapin, qty 6, total NPR 1479").

IMPORTANT: `price` below is total_cost / quantity from that purchase
record, i.e. this clinic's own per-unit COST, NOT a real retail/selling
price -- there is no markup applied. Every price here needs review and a
real markup applied in Django admin (Pharmacy products) before real use,
same caveat as seed_lab_tests's placeholder prices. category/description/
image are intentionally blank (not in the source data, and not needed for
patients to find these by name search) -- fill in later if the storefront
grows enough to need category browsing.

Safe to re-run: uses get_or_create on `name`, so re-running after editing
this list never duplicates and never overwrites a price already corrected
in admin (see PANTOP -- once someone edits it in admin, this command
leaves it alone on future runs).

Usage: python manage.py seed_pharmacy_products
"""
from django.core.management.base import BaseCommand
from marketplace_app.models import PharmacyProduct

# (name, placeholder_price_npr_from_cost_per_unit)
PRODUCTS = [
    ('Gabapin', 246.5),
    ('Pantop', 80.0),
    ('Finast', 340.67),
    ('Rosrol 10', 170.0),
    ('Telmisartan', 180.0),
    ('Duvanta 40', 395.0),
    ('Duvanta 20', 206.67),
    ('Syndopa Plus', 59.33),
    ('Fortiplex (Cap)', 66.0),
    ('Auromega', 992.0),
    ('Parmiplex 0.5', 203.33),
    ('Estaglan 4', 390.0),
]


class Command(BaseCommand):
    help = "Seed PharmacyProduct from a supplier purchase record. Safe to re-run."

    def handle(self, *args, **options):
        created, skipped = 0, 0
        for name, price in PRODUCTS:
            _, was_created = PharmacyProduct.objects.get_or_create(
                name=name,
                defaults={
                    'category': '',
                    'description': '',
                    'price': price,
                    'unit': 'per piece',
                    'image': '',
                    'in_stock': True,
                    'is_featured': False,
                    'requires_prescription': False,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Pharmacy products: {created} created, {skipped} already existed ({len(PRODUCTS)} total)."
        ))
        self.stdout.write(self.style.WARNING(
            "Reminder: prices are this clinic's purchase cost per unit (total_cost / quantity "
            "from the supplier record), not a real retail price -- add a markup and correct "
            "every price in Django admin (Pharmacy products) before real use."
        ))
