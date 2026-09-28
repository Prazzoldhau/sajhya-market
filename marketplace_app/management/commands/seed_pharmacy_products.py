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
printed brand AND strength exactly match the row below. Paths here must
include the 'categorized_product/' prefix, matching every other consumer
of PharmacyProduct.image (patient_app._product_photo_url,
physio_api_app._product_image_url, marketplace_app's own templates all
build the URL as STATIC_URL + image verbatim, with no prefix injected).
image is set only if the row doesn't already have one (never overwrites
an admin upload -- image_upload always wins over this field regardless,
see ImageUrlMixin), and requires_prescription is set to True only where
the actual packaging photo shows a printed "Rx" mark -- not
inferred/guessed (and only if the row still has the unreviewed False
default, so it never clobbers an admin correction).

Three rows were renamed after their photos showed the original Excel
label didn't match the actual brand/strength in stock (confirmed by the
user against the physical box): Estaglan 4 -> SL-GAN 1 (Estazolam 1mg),
Parmiplex 0.5 -> Pramipex 0.25 (Pramipexole 0.25mg), Rosrol 10 ->
Rovastin 5 (Rosuvastatin 5mg). RENAMES below applies this rename in
place (same row, same price/history) before PRODUCTS is processed, so
re-running this command never recreates the old-named row.

Usage: python manage.py seed_pharmacy_products
"""
from django.core.management.base import BaseCommand
from marketplace_app.models import PharmacyProduct

# (old_name, new_name) -- applied once; a no-op once the rename has happened
RENAMES = [
    ('Estaglan 4', 'SL-GAN 1'),
    ('Parmiplex 0.5', 'Pramipex 0.25'),
    ('Rosrol 10', 'Rovastin 5'),
]

# (name, placeholder_price_npr_from_cost_per_unit, image_path_or_blank, rx_confirmed_from_packaging_photo)
PRODUCTS = [
    ('Gabapin', 246.5, 'categorized_product/pharmacy/gabapin.jpg', True),
    ('Pantop', 80.0, '', False),
    ('Finast', 340.67, '', False),
    ('Rovastin 5', 170.0, 'categorized_product/pharmacy/rovastin-5.jpg', False),
    ('Telmisartan', 180.0, 'categorized_product/pharmacy/telmisartan.jpg', True),
    ('Duvanta 40', 395.0, 'categorized_product/pharmacy/duvanta-40.jpg', False),
    ('Duvanta 20', 206.67, '', False),
    ('Syndopa Plus', 59.33, 'categorized_product/pharmacy/syndopa-plus.jpg', True),
    ('Fortiplex (Cap)', 66.0, 'categorized_product/pharmacy/fortiplex-cap.jpg', False),
    ('Auromega', 992.0, '', False),
    ('Pramipex 0.25', 203.33, 'categorized_product/pharmacy/pramipex-025.jpg', False),
    ('SL-GAN 1', 390.0, 'categorized_product/pharmacy/sl-gan-1.jpg', False),
]


# One-time correction: an earlier version of this command stored these same
# photos without the 'categorized_product/' prefix, which 404'd (every
# consumer builds the URL as STATIC_URL + image verbatim -- no prefix is
# injected anywhere). Only rewrites rows still holding that exact prior
# wrong value, so it can never touch a path an admin deliberately typed in.
IMAGE_PATH_FIXES = {
    f'pharmacy/{path.rsplit("/", 1)[-1]}': path
    for _, _, path, _ in PRODUCTS if path
}


class Command(BaseCommand):
    help = "Seed PharmacyProduct from a supplier purchase record. Safe to re-run."

    def handle(self, *args, **options):
        fixed = 0
        for wrong, right in IMAGE_PATH_FIXES.items():
            fixed += PharmacyProduct.objects.filter(image=wrong).update(image=right)

        renamed = 0
        for old_name, new_name in RENAMES:
            if PharmacyProduct.objects.filter(name=new_name).exists():
                continue
            row = PharmacyProduct.objects.filter(name=old_name).first()
            if row:
                row.name = new_name
                row.save(update_fields=['name'])
                renamed += 1

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
            f"Pharmacy products: {fixed} image path(s) corrected, {renamed} renamed, {created} created, "
            f"{skipped} already existed ({updated} of those updated with a new photo/Rx flag), "
            f"{len(PRODUCTS)} total."
        ))
        self.stdout.write(self.style.WARNING(
            "Reminder: prices are this clinic's purchase cost per unit (total_cost / quantity "
            "from the supplier record), not a real retail price -- add a markup and correct "
            "every price in Django admin (Pharmacy products) before real use. Several other "
            "products here (e.g. Pantop, Finast, Duvanta) are commonly prescription-only in "
            "practice but have no packaging photo confirming it yet -- review "
            "requires_prescription for all of these in admin."
        ))
