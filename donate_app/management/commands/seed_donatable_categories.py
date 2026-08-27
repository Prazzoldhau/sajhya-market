"""
Seeds DonatableCategory with the starter list of items Sajhya is collecting
for flood-relief donation. No photos are seeded here on purpose -- add real
ones straight in Django admin (Donate app > Donatable categories) whenever
they're ready; the page already falls back to a placeholder icon until then.

Safe to re-run: uses get_or_create on `name`, so re-running after adding
items here just adds anything new, never duplicates or resets is_active/
sort_order you've already changed in admin.

Usage: python manage.py seed_donatable_categories
"""
from django.core.management.base import BaseCommand
from donate_app.models import DonatableCategory

# (name, description, sort_order)
CATEGORIES = [
    ('Wheelchair', 'Manual or electric, any size', 1),
    ('Crutches', 'Pair or single, adjustable preferred', 2),
    ('Walker', 'Standard or wheeled', 3),
    ('Cane / Walking Stick', '', 4),
    ('Toilet Commode Chair', '', 5),
    ('AFO (Ankle-Foot Orthosis)', 'Any size', 6),
    ('Cervical Collar', '', 7),
    ('Other Mobility Aid', "Anything disability-related that's not listed above", 8),
]


class Command(BaseCommand):
    help = "Seed DonatableCategory with the starter flood-relief donation list. Safe to re-run."

    def handle(self, *args, **options):
        created, updated = 0, 0
        for name, description, sort_order in CATEGORIES:
            obj, was_created = DonatableCategory.objects.get_or_create(
                name=name,
                defaults={'description': description, 'sort_order': sort_order, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Donatable categories: {created} created, {updated} already existed ({len(CATEGORIES)} total)."
        ))
        self.stdout.write(self.style.WARNING(
            "Reminder: no photos are seeded -- add real ones in Django admin (Donate app > "
            "Donatable categories) when ready. The page shows a placeholder icon until then."
        ))
