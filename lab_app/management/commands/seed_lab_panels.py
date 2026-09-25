"""
Seeds LabTestPanel with a starter set of bundled test packages, built only
from tests already in the LabTest catalog -- these are the same panels
Nepali diagnostic labs commonly market as fixed-price packages (Diabetes
Panel, Fever Panel, etc).

Test names below were corrected against the catalog actually live in
production (short report-style names like "CBC", "LFT", "RFT (Renal
Function Test)"), NOT the longer descriptive names this file originally
used (e.g. "Complete Blood Count (CBC)") -- those never matched anything
in the real catalog, so every panel silently skipped. There is no HbA1c
test in the current catalog, so Diabetes Panel is fasting/PP/random sugar
only until one is added.

IMPORTANT: bundle prices below are rough placeholders (roughly 10-15% off
the a-la-carte total of the included tests), NOT this clinic's actual price
list -- correct every price in Django admin (Lab test panels) before real
use, same as LabTest's own placeholder prices.

Safe to re-run: uses get_or_create on `name`, updates description/tests/
is_featured/is_active on re-run but never overwrites a price you've already
corrected in admin. Skips (with a warning) any panel whose test names don't
all match the current LabTest catalog, so editing that catalog's names
won't silently create a broken/incomplete panel.

Usage: python manage.py seed_lab_panels
"""
from django.core.management.base import BaseCommand
from lab_app.models import LabTest, LabTestPanel

# (name, description, [test names], placeholder_bundle_price_npr, is_featured)
PANELS = [
    (
        'Diabetes Panel',
        'Fasting, post-meal (PP) and random blood sugar screening.',
        ['Blood Sugar - Fasting', 'Blood Sugar - PP', 'Blood Sugar - Random'],
        130, True,
    ),
    (
        'Cardiology Panel',
        'Cholesterol/triglycerides, inflammation marker, and a cardiac injury marker for cardiovascular risk screening.',
        ['Lipid Profile', 'CRP Quantitative', 'Troponin I'],
        2200, True,
    ),
    (
        'Fever Panel',
        'Covers the most common causes of fever investigated in Nepal -- typhoid, dengue, and a general infection/blood workup.',
        ['CBC', 'Widal Test', 'Dengue NS-1', 'Urine R/E', 'CRP Quantitative'],
        2200, True,
    ),
    (
        'Liver & Hepatitis Panel',
        'Liver function plus Hepatitis B and C screening.',
        ['LFT', 'HBsAg (Spot)', 'HCV (Spot)'],
        1600, False,
    ),
    (
        'Kidney Panel',
        'Renal function, electrolytes, and uric acid.',
        ['RFT (Renal Function Test)', 'Na, K (Sodium, Potassium) Electrolyte', 'Uric Acid'],
        1400, False,
    ),
    (
        'Thyroid & Vitamins Panel',
        'Thyroid function plus the two most commonly deficient vitamins.',
        ['TFT (FT3, FT4, TSH)', '25-OH Vitamin D', 'Vitamin B12'],
        5000, False,
    ),
    (
        'Anemia Panel',
        'Full anemia workup -- blood count, smear, iron stores, and B12.',
        ['CBC', 'Peripheral Blood Smear (PBS)', 'Reticulocyte Count', 'Iron Profile', 'Vitamin B12'],
        3600, False,
    ),
    (
        'Infection Screening Panel',
        'Standard pre-marital/pre-employment infection screen.',
        ['HIV (Spot Test)', 'VDRL Test', 'HBsAg (Spot)', 'HCV (Spot)'],
        1700, False,
    ),
    (
        'Electrolyte & Mineral Panel',
        'Sodium, potassium, calcium, magnesium and phosphorus.',
        ['Na, K (Sodium, Potassium) Electrolyte', 'Calcium', 'Serum Magnesium', 'Phosphorus'],
        1400, False,
    ),
    (
        'Master Health Checkup Panel',
        "Nepal's typical comprehensive executive checkup -- blood count, sugar, liver, kidney, cholesterol, urine, hepatitis B, thyroid and inflammation.",
        [
            'CBC', 'Blood Sugar - Fasting', 'LFT', 'RFT (Renal Function Test)', 'Lipid Profile',
            'Urine R/E', 'HBsAg (Spot)', 'TSH', 'ESR',
        ],
        3800, True,
    ),
]


class Command(BaseCommand):
    help = "Seed LabTestPanel with starter bundled packages. Safe to re-run."

    def handle(self, *args, **options):
        created, updated, skipped = 0, 0, 0

        for name, description, test_names, price, is_featured in PANELS:
            tests = list(LabTest.objects.filter(name__in=test_names))
            found_names = {t.name for t in tests}
            missing = set(test_names) - found_names
            if missing:
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"Skipping '{name}': LabTest catalog is missing {sorted(missing)} "
                    f"-- run seed_lab_tests first, or check for a renamed test."
                ))
                continue

            panel, was_created = LabTestPanel.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'price': price,
                    'is_featured': is_featured,
                    'is_active': True,
                },
            )
            panel.tests.set(tests)
            if was_created:
                created += 1
            else:
                panel.description = description
                panel.is_featured = is_featured
                panel.is_active = True
                panel.save(update_fields=['description', 'is_featured', 'is_active'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Lab test panels: {created} created, {updated} updated, {skipped} skipped ({len(PANELS)} total)."
        ))
        self.stdout.write(self.style.WARNING(
            "Reminder: bundle prices are rough placeholders -- review and correct every "
            "price in Django admin (Lab test panels) before real use."
        ))
