"""
Seeds LabTest with a starter catalog of common blood investigations.

IMPORTANT: prices below are rough placeholders based on typical Nepali
diagnostic lab price ranges, NOT this clinic's actual current price
list -- every price here needs to be corrected in Django admin before
any real patient submits a request against this catalog. The test list
itself is a reasonable general-practice starting point, not a
lab-verified panel; add/remove/deactivate as needed.

Safe to re-run: uses update_or_create on `name`, so re-running after
editing this list just updates category/sample_type/etc., and never
duplicates. It never touches price on re-run once you've corrected it
in admin (see PRESERVE_PRICE_ON_RERUN below).

Usage: python manage.py seed_lab_tests
"""
from django.core.management.base import BaseCommand
from lab_app.models import LabTest

# (name, category, placeholder_price_npr, sample_type, prep_instructions, turnaround_time)
TESTS = [
    # -- Hematology --
    ('Complete Blood Count (CBC)', 'hematology', 400, 'Blood - Venous', '', 'Same day'),
    ('Erythrocyte Sedimentation Rate (ESR)', 'hematology', 250, 'Blood - Venous', '', 'Same day'),
    ('Peripheral Blood Smear', 'hematology', 350, 'Blood - Venous', '', 'Same day'),
    ('Reticulocyte Count', 'hematology', 400, 'Blood - Venous', '', 'Same day'),
    ('Blood Grouping & Rh Factor', 'hematology', 300, 'Blood - Venous', '', 'Same day'),

    # -- Biochemistry --
    ('Fasting Blood Sugar (FBS)', 'biochemistry', 200, 'Blood - Venous', '8-12 hours fasting required', 'Same day'),
    ('Random Blood Sugar (RBS)', 'biochemistry', 200, 'Blood - Venous', '', 'Same day'),
    ('HbA1c (Glycated Hemoglobin)', 'biochemistry', 900, 'Blood - Venous', '', '24 hours'),
    ('Lipid Profile', 'biochemistry', 1000, 'Blood - Venous', '10-12 hours fasting required', '24 hours'),
    ('Liver Function Test (LFT)', 'biochemistry', 900, 'Blood - Venous', '', '24 hours'),
    ('Renal Function Test (RFT/KFT)', 'biochemistry', 800, 'Blood - Venous', '', '24 hours'),
    ('Serum Uric Acid', 'biochemistry', 350, 'Blood - Venous', '', 'Same day'),
    ('Serum Creatinine', 'biochemistry', 300, 'Blood - Venous', '', 'Same day'),
    ('Serum Amylase', 'biochemistry', 700, 'Blood - Venous', '', '24 hours'),
    ('C-Reactive Protein (CRP)', 'biochemistry', 700, 'Blood - Venous', '', 'Same day'),

    # -- Hormonal --
    ('Thyroid Profile (TSH, T3, T4)', 'hormonal', 1300, 'Blood - Venous', '', '24 hours'),
    ('TSH Only', 'hormonal', 600, 'Blood - Venous', '', '24 hours'),
    ('Serum Cortisol', 'hormonal', 1500, 'Blood - Venous', '', '48 hours'),
    ('Vitamin D (25-OH)', 'hormonal', 3000, 'Blood - Venous', '', '48-72 hours'),
    ('Vitamin B12', 'hormonal', 2000, 'Blood - Venous', '', '24-48 hours'),
    ('Serum Ferritin', 'hormonal', 1500, 'Blood - Venous', '', '24 hours'),

    # -- Serology / Infection --
    ('HIV Screening', 'serology', 600, 'Blood - Venous', '', 'Same day'),
    ('HBsAg (Hepatitis B)', 'serology', 500, 'Blood - Venous', '', 'Same day'),
    ('Anti-HCV (Hepatitis C)', 'serology', 700, 'Blood - Venous', '', 'Same day'),
    ('Widal Test (Typhoid)', 'serology', 400, 'Blood - Venous', '', 'Same day'),
    ('VDRL (Syphilis)', 'serology', 400, 'Blood - Venous', '', 'Same day'),
    ('Dengue NS1/IgG/IgM', 'serology', 1200, 'Blood - Venous', '', 'Same day'),

    # -- Electrolytes & Minerals --
    ('Serum Electrolytes (Na, K, Cl)', 'electrolytes', 700, 'Blood - Venous', '', 'Same day'),
    ('Serum Calcium', 'electrolytes', 350, 'Blood - Venous', '', 'Same day'),
    ('Serum Magnesium', 'electrolytes', 500, 'Blood - Venous', '', 'Same day'),
    ('Serum Phosphorus', 'electrolytes', 350, 'Blood - Venous', '', 'Same day'),

    # -- Urine --
    ('Urine Routine & Microscopy (R/E)', 'urine', 250, 'Urine - Midstream', '', 'Same day'),
    ('Urine Culture & Sensitivity', 'urine', 800, 'Urine - Midstream', '', '48-72 hours'),
]


class Command(BaseCommand):
    help = "Seed LabTest with a starter blood-investigation catalog. Safe to re-run."

    def handle(self, *args, **options):
        created, updated = 0, 0
        for name, category, price, sample_type, prep, turnaround in TESTS:
            # get_or_create (not update_or_create): price is only ever set
            # via `defaults` on the create path below. Re-running this
            # command after a clinic has corrected real prices in admin
            # must never silently overwrite them back to the placeholder.
            obj, was_created = LabTest.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'price': price,
                    'sample_type': sample_type,
                    'prep_instructions': prep,
                    'turnaround_time': turnaround,
                    'is_active': True,
                },
            )
            if was_created:
                created += 1
            else:
                obj.category = category
                obj.sample_type = sample_type
                obj.prep_instructions = prep
                obj.turnaround_time = turnaround
                obj.is_active = True
                obj.save(update_fields=['category', 'sample_type', 'prep_instructions', 'turnaround_time', 'is_active'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Lab tests: {created} created, {updated} updated ({len(TESTS)} total)."
        ))
        self.stdout.write(self.style.WARNING(
            "Reminder: prices are rough placeholders, not this clinic's real price list -- "
            "review and correct every price in Django admin (Lab tests) before real use."
        ))
