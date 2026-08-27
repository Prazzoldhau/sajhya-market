"""
Seeds DonatableCategory with the list of items Sajhya is collecting for
flood-relief donation. Photo-backed items (real product photos already
committed to static/categorized_product/donate/) are seeded with their
image path set directly; the rest start with no image and fall back to a
placeholder icon until a photo's added -- either by editing this list and
re-running, or straight in Django admin.

Safe to re-run: uses get_or_create on `name`, so re-running after adding
items here just adds anything new and updates image/description/sort_order
for existing ones, never duplicates or resets is_active you've changed in
admin.

Usage: python manage.py seed_donatable_categories
"""
from django.core.management.base import BaseCommand
from donate_app.models import DonatableCategory

# (name, description, image_path, sort_order)
CATEGORIES = [
    ('Wheelchair', 'Manual or electric, any size', 'categorized_product/donate/wheelchair.jpg', 1),
    ('Crutches', 'Underarm, pair or single, adjustable preferred', 'categorized_product/donate/crutches.jpg', 2),
    ('Elbow Crutch', 'Forearm / Lofstrand style, pair', 'categorized_product/donate/elbow-crutch.jpg', 3),
    ('Walker', 'Standard or wheeled', 'categorized_product/donate/walker.jpg', 4),
    ('Toilet Commode Chair', '', 'categorized_product/donate/toilet-commode-chair.jpg', 5),
    ('Elbow Immobilizer', '', 'categorized_product/donate/elbow-immobilizer.jpg', 6),
    ('Elbow ROM Brace', 'Adjustable range-of-motion brace', 'categorized_product/donate/elbow-rom-brace.jpg', 7),
    ('Knee Immobilizer', '', 'categorized_product/donate/knee-immobilizer.jpg', 8),
    ('Knee ROM Brace', 'Adjustable range-of-motion brace', 'categorized_product/donate/knee-rom-brace.jpg', 9),
    ('Air Mattress', 'Anti-bedsore alternating-pressure mattress with pump', 'categorized_product/donate/air-mattress.jpg', 10),
    ('Cane / Walking Stick', '', '', 11),
    ('AFO (Ankle-Foot Orthosis)', 'Any size', '', 12),
    ('Cervical Collar', '', '', 13),
    ('Other Mobility Aid', "Anything disability-related that's not listed above", '', 14),
]


class Command(BaseCommand):
    help = "Seed DonatableCategory with the flood-relief donation list. Safe to re-run."

    def handle(self, *args, **options):
        created, updated = 0, 0
        for name, description, image, sort_order in CATEGORIES:
            obj, was_created = DonatableCategory.objects.get_or_create(
                name=name,
                defaults={'description': description, 'image': image, 'sort_order': sort_order, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                obj.description = description
                obj.image = image
                obj.sort_order = sort_order
                obj.save(update_fields=['description', 'image', 'sort_order'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Donatable categories: {created} created, {updated} updated ({len(CATEGORIES)} total)."
        ))
