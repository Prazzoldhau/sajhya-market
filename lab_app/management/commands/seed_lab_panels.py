"""
Seeds LabTestPanel with a starter set of bundled test packages, built only
from tests already in the LabTest catalog (see seed_lab_tests) -- these are
the same panels Nepali diagnostic labs commonly market as fixed-price
packages (Diabetes Panel, Fever Panel, etc).

IMPORTANT: bundle prices below are rough placeholders (roughly 10-15% off
the a-la-carte total of the included tests), NOT this clinic's actual price
list -- correct every price in Django admin (Lab test panels) before real
use, same as LabTest's own placeholder prices.

Safe to re-run: uses get_or_create on `name`, updates description/tests/
is_featured/is_active on re-run but never overwrites a price you've already
corrected in admin. Skips (with a warning) any panel whose test names don't
all match the current LabTest catalog, so editing that catalog's names
won't silently create a broken/incomplete panel.

Usage: python manage.py seed_lab_panels (run after seed_lab_tests)
"""
from django.core.management.base import BaseCommand
from lab_app.models import LabTest, LabTestPanel

# (name, description, [test names], placeholder_bundle_price_npr, is_featured)
PANELS = [
    (
        'Diabetes Panel',
        'Fasting & random blood sugar plus 3-month average control (HbA1c).',
        ['Fasting Blood Sugar (FBS)', 'Random Blood Sugar (RBS)', 'HbA1c (Glycated Hemoglobin)'],
        1100, True,
    ),
    (
        'Cardiology Panel',
        'Cholesterol/triglycerides and inflammation marker for cardiovascular risk screening.',
        ['Lipid Profile', 'C-Reactive Protein (CRP)'],
        1500, True,
    ),
    (
        'Fever Panel',
        'Covers the most common causes of fever investigated in Nepal -- typhoid, dengue, and a general infection/blood workup.',
        ['Complete Blood Count (CBC)', 'Widal Test (Typhoid)', 'Dengue NS1/IgG/IgM', 'Urine Routine & Microscopy (R/E)', 'C-Reactive Protein (CRP)'],
        2500, True,
    ),
    (
        'Liver & Hepatitis Panel',
        'Liver function plus Hepatitis B and C screening.',
        ['Liver Function Test (LFT)', 'HBsAg (Hepatitis B)', 'Anti-HCV (Hepatitis C)'],
        1800, False,
    ),
    (
        'Kidney Panel',
        'Renal function, electrolytes, and uric acid.',
        ['Renal Function Test (RFT/KFT)', 'Serum Electrolytes (Na, K, Cl)', 'Serum Uric Acid'],
        1600, False,
    ),
    (
        'Thyroid & Vitamins Panel',
        'Thyroid function plus the two most commonly deficient vitamins.',
        ['Thyroid Profile (TSH, T3, T4)', 'Vitamin D (25-OH)', 'Vitamin B12'],
        5500, False,
    ),
    (
        'Anemia Panel',
        'Full anemia workup -- blood count, smear, iron stores, and B12.',
        ['Complete Blood Count (CBC)', 'Peripheral Blood Smear', 'Reticulocyte Count', 'Serum Ferritin', 'Vitamin B12'],
        4000, False,
    ),
    (
        'Infection Screening Panel',
        'Standard pre-marital/pre-employment infection screen.',
        ['HIV Screening', 'VDRL (Syphilis)', 'HBsAg (Hepatitis B)', 'Anti-HCV (Hepatitis C)'],
        1900, False,
    ),
    (
        'Electrolyte & Mineral Panel',
        'Sodium, potassium, chloride, calcium, magnesium and phosphorus.',
        ['Serum Electrolytes (Na, K, Cl)', 'Serum Calcium', 'Serum Magnesium', 'Serum Phosphorus'],
        1600, False,
    ),
    (
        'Master Health Checkup Panel',
        "Nepal's typical comprehensive executive checkup -- blood count, sugar, liver, kidney, cholesterol, urine, hepatitis B, thyroid and inflammation.",
        [
            'Complete Blood Count (CBC)', 'Fasting Blood Sugar (FBS)', 'Liver Function Test (LFT)',
            'Renal Function Test (RFT/KFT)', 'Lipid Profile', 'Urine Routine & Microscopy (R/E)',
            'HBsAg (Hepatitis B)', 'TSH Only', 'Erythrocyte Sedimentation Rate (ESR)',
        ],
        4200, True,
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
