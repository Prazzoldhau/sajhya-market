"""
Seeds DiagnosisCode with a starter set of ICD-10 codes relevant to
physiotherapy practice, drawn from the free-text patient_diagnosis values
actually seen in this clinic's data (low back pain / IVDP variants, knee
and shoulder conditions, tennis elbow, plantar fasciitis, stroke/hemiplegia,
Parkinson's, ligament/meniscus injuries, post-op rehab, autism).

IMPORTANT: this list was drafted for coverage, not verified against an
authoritative ICD-10 terminology server. Review before relying on it for
real records, billing, or reporting -- deactivate (don't delete) anything
wrong or unwanted via Django admin, since patients may already reference
a code by the time it's noticed.

Safe to re-run: uses update_or_create on `code`, so re-running after
editing this list just updates labels/chapters, and never duplicates.

Usage: python manage.py seed_diagnosis_codes
"""
from django.core.management.base import BaseCommand
from personal_account.models import DiagnosisCode

CODES = [
    # (code, label, chapter)

    # -- Musculoskeletal (M-chapter): the bulk of this clinic's caseload --
    ('M54.5', 'Low back pain', 'Musculoskeletal'),
    ('M54.4', 'Lumbago with sciatica', 'Musculoskeletal'),
    ('M54.2', 'Cervicalgia (neck pain)', 'Musculoskeletal'),
    ('M51.1', 'Lumbar disc disorder with radiculopathy', 'Musculoskeletal'),
    ('M51.9', 'Intervertebral disc disorder, unspecified (IVDP)', 'Musculoskeletal'),
    ('M50.1', 'Cervical disc disorder with radiculopathy', 'Musculoskeletal'),
    ('M50.9', 'Cervical disc disorder, unspecified', 'Musculoskeletal'),
    ('M47.9', 'Spondylosis, unspecified', 'Musculoskeletal'),
    ('M53.1', 'Cervicobrachial syndrome', 'Musculoskeletal'),
    ('M17.9', 'Osteoarthritis of knee, unspecified', 'Musculoskeletal'),
    ('M19.90', 'Osteoarthritis, unspecified site', 'Musculoskeletal'),
    ('M75.4', 'Impingement syndrome of shoulder', 'Musculoskeletal'),
    ('M75.1', 'Rotator cuff syndrome / tear', 'Musculoskeletal'),
    ('M75.0', 'Adhesive capsulitis of shoulder (frozen shoulder)', 'Musculoskeletal'),
    ('M77.1', 'Lateral epicondylitis (tennis elbow)', 'Musculoskeletal'),
    ('M77.0', 'Medial epicondylitis (golfer\'s elbow)', 'Musculoskeletal'),
    ('M72.2', 'Plantar fascial fibromatosis (plantar fasciitis)', 'Musculoskeletal'),
    ('M79.1', 'Myalgia', 'Musculoskeletal'),
    ('M79.7', 'Fibromyalgia', 'Musculoskeletal'),
    ('M62.83', 'Muscle spasm', 'Musculoskeletal'),
    ('M25.5', 'Pain in joint', 'Musculoskeletal'),
    ('M96.1', 'Post-laminectomy syndrome', 'Musculoskeletal'),

    # -- Neurological --
    ('G81.9', 'Hemiplegia, unspecified', 'Neurological'),
    ('I69.3', 'Sequelae of cerebral infarction (stroke)', 'Neurological'),
    ('I69.4', 'Sequelae of stroke, unspecified', 'Neurological'),
    ('G20', "Parkinson's disease", 'Neurological'),
    ('G35', 'Multiple sclerosis', 'Neurological'),
    ('G57.3', 'Lesion of peroneal nerve (foot drop)', 'Neurological'),
    ('G82.20', 'Paraplegia, unspecified', 'Neurological'),

    # -- Injury (S-chapter) --
    ('S83.5', 'Sprain of anterior cruciate ligament of knee', 'Injury'),
    ('S83.2', 'Tear of meniscus, current injury', 'Injury'),
    ('S43.0', 'Dislocation of shoulder joint', 'Injury'),
    ('S93.4', 'Sprain of ankle', 'Injury'),

    # -- Aftercare / rehabilitation (Z-chapter) --
    ('Z47.1', 'Aftercare following joint replacement surgery', 'Aftercare'),
    ('Z96.6', 'Presence of orthopedic joint implants', 'Aftercare'),
    ('Z50.1', 'Encounter for physical therapy session', 'Aftercare'),
    ('Z98.89', 'Other specified postprocedural states (post-fracture rehab)', 'Aftercare'),

    # -- Developmental --
    ('F84.0', 'Autism spectrum disorder', 'Developmental'),

    # -- Fallback --
    ('R99', 'Other/unspecified — use free-text diagnosis for detail', 'Other'),
]


class Command(BaseCommand):
    help = "Seed DiagnosisCode with a starter ICD-10 list for physiotherapy. Safe to re-run."

    def handle(self, *args, **options):
        created, updated = 0, 0
        for code, label, chapter in CODES:
            obj, was_created = DiagnosisCode.objects.update_or_create(
                code=code,
                defaults={'label': label, 'chapter': chapter, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Diagnosis codes: {created} created, {updated} updated ({len(CODES)} total)."
        ))
        self.stdout.write(self.style.WARNING(
            "Reminder: this list is a starting point, not a verified clinical mapping -- "
            "review it (Django admin > Diagnosis codes) before relying on it for real records."
        ))
