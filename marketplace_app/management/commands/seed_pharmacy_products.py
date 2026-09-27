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

Real box/blister photos for a few of these were added later (see
static/categorized_product/pharmacy/) -- matched only where the photo's
printed brand AND strength exactly match the row below. image is set only
if the row doesn't already have one (never overwrites an admin upload),
and requires_prescription is set to True only where the actual packaging
photo shows a printed "Rx" mark -- not inferred/guessed (and only if the
row still has the unreviewed False default, so it never clobbers an
admin correction).

Usage: python manage.py seed_pharmacy_products
"""
from django.core.management.base import BaseCommand
from marketplace_app.models import PharmacyProduct

# (name, placeholder_price_npr_from_cost_per_unit, image_path_or_blank, rx_confirmed_from_packaging_photo)
PRODUCTS = [
    ('Gabapin', 246.5, 'pharmacy/gabapin.jpg', True),
    ('Pantop', 80.0, '', False),
    ('Finast', 340.67, '', False),
    ('Rosrol 10', 170.0, '', False),
    ('Telmisartan', 180.0, 'pharmacy/telmisartan.jpg', True),
    ('Duvanta 40', 395.0, 'pharmacy/duvanta-40.jpg', False),
    ('Duvanta 20', 206.67, '', False),
    ('Syndopa Plus', 59.33, 'pharmacy/syndopa-plus.jpg', True),
    ('Fortiplex (Cap)', 66.0, 'pharmacy/fortiplex-cap.jpg', False),
    ('Auromega', 992.0, '', False),
    ('Parmiplex 0.5', 203.33, '', False),
    ('Estaglan 4', 390.0, '', False),
]


class Command(BaseCommand):
    help = "Seed PharmacyProduct from a supplier purchase record. Safe to re-run."

    def handle(self, *args, **options):
        created, skipped, updated = 0, 0, 0
        for name, price, image, rx_confirmed in PRODUCTS:
            obj, was_created = PharmacyProduct.objects.get_or_create(
                name=name,
                defaults={
                    'category': '',
                    'description': '',
                    'price': price,
                    'unit': 'per piece',
                    'image': image,
                    'in_stock': True,
                    'is_featured': False,
                    'requires_prescription': rx_confirmed,
                },
            )
            if was_created:
                created += 1
                continue

            skipped += 1
            changed = False
            if image and not obj.image:
                obj.image = image
                changed = True
            if rx_confirmed and not obj.requires_prescription:
                obj.requires_prescription = True
                changed = True
            if changed:
                obj.save(update_fields=['image', 'requires_prescription'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Pharmacy products: {created} created, {skipped} already existed "
            f"({updated} of those updated with a new photo/Rx flag), {len(PRODUCTS)} total."
        ))
        self.stdout.write(self.style.WARNING(
            "Reminder: prices are this clinic's purchase cost per unit (total_cost / quantity "
            "from the supplier record), not a real retail price -- add a markup and correct "
            "every price in Django admin (Pharmacy products) before real use. Several other "
            "products here (e.g. Pantop, Finast, Duvanta) are commonly prescription-only in "
            "practice but have no packaging photo confirming it yet -- review "
            "requires_prescription for all of these in admin."
        ))
