"""
Aggregate, de-identified usage report for the Sajhya patient app.

Produces counts/percentages only -- no patient name, contact, patient_code,
or other PII is read or printed. Intended as the data source for the
"Usage Data" section of a technology-description manuscript.

Usage:
    python manage.py usage_report
    python manage.py usage_report --json report.json
"""
import json
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from personal_account.models import AddPatient, PatientPhysioPairing
from exercise_app.models import (
    Region, SubRegion, ExerciseMain, Prescription, PrescriptionExercise, ExerciseFeedback,
)


def pct(part, whole):
    return round((part / whole) * 100, 1) if whole else 0.0


class Command(BaseCommand):
    help = "Print an aggregate, de-identified usage report for the patient app (no PII)."

    def add_arguments(self, parser):
        parser.add_argument('--json', dest='json_path', default=None,
                             help='Also write the report as JSON to this path.')

    def handle(self, *args, **options):
        report = {}

        # ---- Patients ----------------------------------------------------
        patients = AddPatient.objects.filter(is_deleted=False)
        total_patients = patients.count()

        pairing_source_counts = dict(
            PatientPhysioPairing.objects.values('source').annotate(n=Count('id')).values_list('source', 'n')
        )
        # Fallback for patients with no PatientPhysioPairing row: bucket by
        # whether they set their own password (self-registered) or not.
        unpaired = total_patients - sum(pairing_source_counts.values())

        registrations_by_month = defaultdict(int)
        for created_at in patients.values_list('created_at', flat=True):
            if created_at:
                registrations_by_month[created_at.strftime('%Y-%m')] += 1
        registrations_by_month = dict(sorted(registrations_by_month.items()))

        first_reg = patients.order_by('created_at').values_list('created_at', flat=True).first()
        last_reg = patients.order_by('-created_at').values_list('created_at', flat=True).first()

        report['patients'] = {
            'total_active_patients': total_patients,
            'by_pairing_source': pairing_source_counts,
            'unpaired_or_legacy': unpaired,
            'registrations_by_month': registrations_by_month,
            'first_registration': first_reg.isoformat() if first_reg else None,
            'last_registration': last_reg.isoformat() if last_reg else None,
        }

        # ---- Physios actively prescribing ---------------------------------
        prescribing_physios = Prescription.objects.values('created_by').distinct().count()
        report['prescribing_physios'] = prescribing_physios

        # ---- Prescriptions --------------------------------------------------
        prescriptions = Prescription.objects.all()
        total_prescriptions = prescriptions.count()
        status_counts = dict(prescriptions.values('status').annotate(n=Count('id')).values_list('status', 'n'))
        patients_with_prescription = prescriptions.values('patient').distinct().count()

        report['prescriptions'] = {
            'total': total_prescriptions,
            'by_status': status_counts,
            'distinct_patients_prescribed': patients_with_prescription,
            'pct_patients_with_a_prescription': pct(patients_with_prescription, total_patients),
        }

        # ---- Prescribed exercises / adherence ------------------------------
        pex = PrescriptionExercise.objects.all()
        total_pex = pex.count()
        completed_pex = pex.filter(is_completed=True).count()

        report['adherence'] = {
            'total_exercises_assigned': total_pex,
            'total_exercises_completed': completed_pex,
            'overall_completion_rate_pct': pct(completed_pex, total_pex),
            'avg_exercises_per_prescribed_patient': round(total_pex / patients_with_prescription, 1) if patients_with_prescription else 0,
        }

        # ---- Region-level breakdown ------------------------------------------
        region_totals = Counter()
        region_completed = Counter()
        for row in pex.select_related('exercise__sub_region_fk__region_fk'):
            region_name = None
            if row.exercise and row.exercise.sub_region_fk and row.exercise.sub_region_fk.region_fk:
                region_name = row.exercise.sub_region_fk.region_fk.region_name
            else:
                # Exercise link was cleared (SET_NULL on delete) -- fall back
                # to looking the snapshot id up directly.
                ex = ExerciseMain.objects.filter(id=row.exercise_id_in_library).select_related(
                    'sub_region_fk__region_fk').first()
                if ex and ex.sub_region_fk and ex.sub_region_fk.region_fk:
                    region_name = ex.sub_region_fk.region_fk.region_name
            region_name = region_name or 'Unknown/legacy'
            region_totals[region_name] += 1
            if row.is_completed:
                region_completed[region_name] += 1

        report['by_region'] = {
            region: {
                'assigned': region_totals[region],
                'completed': region_completed[region],
                'completion_rate_pct': pct(region_completed[region], region_totals[region]),
            }
            for region in sorted(region_totals, key=lambda r: -region_totals[r])
        }

        # ---- Exercise feedback (safety signal) -------------------------------
        feedback_counts = dict(
            ExerciseFeedback.objects.values('feedback_type').annotate(n=Count('id')).values_list('feedback_type', 'n')
        )
        total_feedback = sum(feedback_counts.values())
        concerning = feedback_counts.get('painful', 0) + feedback_counts.get('increased_symptom', 0)

        report['feedback'] = {
            'total_feedback_logged': total_feedback,
            'by_type': feedback_counts,
            'pct_of_completed_exercises_with_feedback': pct(total_feedback, completed_pex),
            'pct_feedback_painful_or_increased_symptom': pct(concerning, total_feedback),
        }

        # ---- Content library (supports "bilingual, video-supported" claims) --
        exercises = ExerciseMain.objects.all()
        total_exercises = exercises.count()
        with_nepali = exercises.exclude(Q(exercise_description_nepali='') | Q(exercise_description_nepali__isnull=True)).count()
        with_video = exercises.exclude(Q(youtube_url='') | Q(youtube_url__isnull=True)).count()
        regions_covered = Region.objects.count()
        subregions_covered = SubRegion.objects.count()

        report['content_library'] = {
            'total_exercises': total_exercises,
            'regions': regions_covered,
            'sub_regions': subregions_covered,
            'with_nepali_translation': with_nepali,
            'pct_with_nepali_translation': pct(with_nepali, total_exercises),
            'with_youtube_video': with_video,
            'pct_with_youtube_video': pct(with_video, total_exercises),
        }

        # ---- Print ------------------------------------------------------------
        self.stdout.write(self.style.SUCCESS('\n=== Sajhya Patient App -- Aggregate Usage Report (de-identified) ===\n'))
        self.stdout.write(json.dumps(report, indent=2, ensure_ascii=False))

        if options['json_path']:
            with open(options['json_path'], 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            self.stdout.write(self.style.SUCCESS(f"\nWritten to {options['json_path']}"))
