from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from datetime import date
from django.utils.dateparse import parse_date
from personal_account.models import (
    AddPatient, Clinic, PatientMedicalProfile, PatientMedication,
    PatientBloodTest, PatientAid, PatientAssessmentEntry, PatientDietEntry,
    PatientConsultation, Rx,
)
from exercise_app.models import Prescription, PrescriptionExercise, ExerciseFeedback
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from prescription_app.models import TreatmentSession
from marketplace_app.views import get_recommended_for_diagnosis
from marketplace_app.models import PatientProductRecommendation, Product, PharmacyProduct
from lab_app.models import LabTest
from assessment_app.models import SpecialTestReference
from patient_app.views import _medical_profile_context, _attach_medical_profile_urls


# Create your views here.
def patient_detail(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    sessions = TreatmentSession.objects.filter(patient_id=patient_id).only(
        'session_date', 'session_number', 'treatment_response'
    )
    # Excludes Pharmacy same as every other Marketplace listing; nothing
    # stops a physio from picking a Pharmacy product here otherwise, which
    # would leak it out of its own tab.
    manual_recs = (
        PatientProductRecommendation.objects.filter(patient=patient)
        .exclude(product__category__name='Pharmacy')
        .select_related('product', 'product__category')
    )
    manual_ids = list(manual_recs.values_list('product_id', flat=True))
    auto_recommended, matched_label = get_recommended_for_diagnosis(patient.patient_diagnosis)
    auto_recommended = auto_recommended.exclude(id__in=manual_ids).select_related('category')[:4]

    context = {
        "sessions": sessions,
        "patient": patient,
        "manual_recs": manual_recs,
        "auto_recommended": auto_recommended,
        "matched_label": matched_label,
        "medical_profile": getattr(patient, 'medical_profile', None),
        "medications": patient.medications.select_related('pharmacy_product'),
        "blood_tests": patient.blood_test_entries.select_related('lab_test'),
    }
    return render(request, 'patient-detail-dashboard.html', context)


def patient_exercise_status(request, patient_id):
   
    """View to display all prescriptions for a patient"""
    patient = get_object_or_404(AddPatient, id=patient_id)
    # clinic_id = patient.origin_clinic.id   # Get clinic ID from patient
    # clinic_id = patient.origin_clinic.id if patient.origin_clinic else '',
    clinic_id = patient.origin_clinic.id if patient.origin_clinic else None
    prescriptions = Prescription.objects.filter(patient=patient).order_by('-created_at')
    
    user = request.user
    userType = user.user_type


    
    # Calculate statistics
    total_prescriptions = prescriptions.count()
    active_prescriptions = prescriptions.filter(status='active').count()
    completed_prescriptions = prescriptions.filter(status='completed').count()
    
    # Prepare prescriptions data with exercises
    prescriptions_data = []
    for prescription in prescriptions:
        exercises = prescription.exercises.all().order_by('order')
        
        # Calculate progress
        total_exercises = exercises.count()
        completed_exercises = exercises.filter(is_completed=True).count()

        
        # Check if prescription is active
        today = date.today()
        is_active = (prescription.status == 'active')
        
        exercises_with_feedback = []
        for ex in exercises:
            feedback_logs = ex.feedback_logs.order_by('-logged_at')[:5]
            exercises_with_feedback.append({
                'exercise': ex,
                'feedback_logs': feedback_logs,
            })

        prescriptions_data.append({
            'prescription': prescription,
            'exercises': exercises,
            'exercises_with_feedback': exercises_with_feedback,
            'total_exercises': total_exercises,
            'completed_exercises': completed_exercises,
            'is_active': is_active,
        })
    
    context = {
        'patient': patient,
        'prescriptions': prescriptions_data,
        'total_prescriptions': total_prescriptions,
        'active_prescriptions': active_prescriptions,
        'completed_prescriptions': completed_prescriptions,
        'clinic_id': clinic_id,
        'today': date.today(),
        "user_type": userType,
    }
    
    
    return render (request, 'patient-exercise-state.html', context)




def latest_prescription(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    latest_prescription = Prescription.objects.filter(patient=patient).order_by('-created_at').first()
    if not latest_prescription:
        return JsonResponse({'error': 'No prescription found'}, status=404)
    
    exercises_list = []
    for ex in latest_prescription.exercises.all().order_by('order'):
        exercises_list.append({
            # 'id': ex.id,
            'exercise_name': ex.exercise_name,
            'difficulty_level': ex.difficulty_level,
            # 'sets': getattr(ex, 'sets', None),   # adjust to your through model
            # 'reps': getattr(ex, 'reps', None),
            'is_completed': getattr(ex, 'is_completed', False),
        })
    
    return JsonResponse({
        'prescription_id': latest_prescription.id,
        'status': latest_prescription.status,
        'start_date': latest_prescription.start_date.isoformat() if latest_prescription.start_date else None,
        'end_date': latest_prescription.end_date.isoformat() if latest_prescription.end_date else None,
        'exercises': exercises_list,
    })


@csrf_exempt
@require_http_methods(["POST"])
def toggle_exercise_completion(request, exercise_id):
    try:
        exercise = PrescriptionExercise.objects.get(id=exercise_id)
        data = json.loads(request.body)
        is_completed = data.get('is_completed', False)

        exercise.is_completed = is_completed
        exercise.completed_at = timezone.now() if is_completed else None
        exercise.save()

        # Get the parent prescription
        prescription = exercise.prescription
        exercises = prescription.exercises.all()
        total_exercises = exercises.count()
        completed_exercises = exercises.filter(is_completed=True).count()
        progress_percentage = (completed_exercises / total_exercises * 100) if total_exercises > 0 else 0

        # Check if the prescription just became fully completed
        just_completed = (completed_exercises == total_exercises) and total_exercises > 0

        return JsonResponse({
            'success': True,
            'prescription_id': prescription.id,
            'completed_exercises': completed_exercises,
            'total_exercises': total_exercises,
            'progress_percentage': round(progress_percentage, 1),
            'prescription_completed': just_completed,
            'exercise_id': exercise_id,
            'is_completed': is_completed
        })

    except PrescriptionExercise.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Exercise not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    
@csrf_exempt
@require_http_methods(["POST"])
def remove_prescription_exercise(request, exercise_id):
    try:
        exercise = PrescriptionExercise.objects.get(id=exercise_id)
        prescription = exercise.prescription
        exercise.delete()

        exercises = prescription.exercises.all()
        total_exercises = exercises.count()
        completed_exercises = exercises.filter(is_completed=True).count()
        progress_percentage = (completed_exercises / total_exercises * 100) if total_exercises > 0 else 0

        return JsonResponse({
            'success': True,
            'prescription_id': prescription.id,
            'completed_exercises': completed_exercises,
            'total_exercises': total_exercises,
            'progress_percentage': round(progress_percentage, 1),
        })
    except PrescriptionExercise.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Exercise not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def update_exercise_params(request, exercise_id):
    try:
        exercise = PrescriptionExercise.objects.get(id=exercise_id)
        data = json.loads(request.body)

        exercise.sets = int(data.get('sets', exercise.sets))
        exercise.reps = int(data.get('reps', exercise.reps))
        exercise.hold_time_sec = int(data.get('hold_time_sec', exercise.hold_time_sec))
        exercise.rest_time_sec = int(data.get('rest_time_sec', exercise.rest_time_sec))
        exercise.schedule_morning = bool(data.get('schedule_morning', exercise.schedule_morning))
        exercise.schedule_day = bool(data.get('schedule_day', exercise.schedule_day))
        exercise.schedule_evening = bool(data.get('schedule_evening', exercise.schedule_evening))
        exercise.save(update_fields=[
            'sets', 'reps', 'hold_time_sec', 'rest_time_sec',
            'schedule_morning', 'schedule_day', 'schedule_evening', 'updated_at',
        ])

        return JsonResponse({
            'success': True,
            'sets': exercise.sets,
            'reps': exercise.reps,
            'hold_time_sec': exercise.hold_time_sec,
            'rest_time_sec': exercise.rest_time_sec,
            'schedule_morning': exercise.schedule_morning,
            'schedule_day': exercise.schedule_day,
            'schedule_evening': exercise.schedule_evening,
        })
    except PrescriptionExercise.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Exercise not found'}, status=404)
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': f'Invalid value: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def refer_to(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)

    return render (request, 'refer.html', {'patient': patient})


# ==================== PHYSIO-FACING MEDICAL PROFILE EDITOR ====================
# Same page/models patient_app.patient_medical_profile_page and friends edit
# for the patient themselves -- a physio can now fill in or correct the same
# data (confirming a medication after review, adding one a patient forgot,
# etc.), recorded with `recorded_by`/`last_updated_by` set so it's clear who
# added what (see those fields on the personal_account models this touches).
# Shares _medical_profile_context with the patient-facing view so the two
# never drift out of sync on what data the page shows.

def _physio_tab_redirect(patient_id, tab, subtab=None):
    url = f"{reverse('physio-medical-profile', kwargs={'patient_id': patient_id})}?tab={tab}"
    if subtab:
        url += f"&subtab={subtab}"
    return redirect(url)


@login_required
def physio_medical_profile_page(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    profile, _ = PatientMedicalProfile.objects.get_or_create(patient=patient)

    saved = False
    if request.method == "POST":
        for field in ('allergies', 'medical_history', 'nursing_vitals',
                      'nursing_wound_catheter_care', 'nursing_mobility_assistance'):
            if field in request.POST:
                setattr(profile, field, request.POST.get(field, '').strip())
        profile.last_updated_by = request.user
        profile.save()
        saved = True

    context = _medical_profile_context(patient)
    context.update({
        'profile': profile,
        'saved': saved,
        'editing_patient_id': patient.id,
    })
    _attach_medical_profile_urls(context, patient, is_physio=True)
    return render(request, 'patient-medical-profile.html', context)


@login_required
def physio_medication_add(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    if request.method == "POST":
        time_of_day = request.POST.get('time_of_day', '').strip()
        pharmacy_product_id = request.POST.get('pharmacy_product_id', '').strip()
        custom_name = request.POST.get('custom_name', '').strip()
        instructions = request.POST.get('instructions', '').strip()
        if time_of_day in dict(PatientMedication.TIME_CHOICES) and (pharmacy_product_id or custom_name):
            pharmacy_product = PharmacyProduct.objects.filter(id=pharmacy_product_id).first() if pharmacy_product_id else None
            PatientMedication.objects.create(
                patient=patient, time_of_day=time_of_day, pharmacy_product=pharmacy_product,
                custom_name='' if pharmacy_product else custom_name, instructions=instructions,
                recorded_by=request.user,
            )
    return _physio_tab_redirect(patient_id, 'medication')


@login_required
def physio_medication_delete(request, patient_id, medication_id):
    if request.method == "POST":
        PatientMedication.objects.filter(id=medication_id, patient_id=patient_id).delete()
    return _physio_tab_redirect(patient_id, 'medication')


@login_required
def physio_bloodtest_add(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    if request.method == "POST":
        lab_test_id = request.POST.get('lab_test_id', '').strip()
        custom_name = request.POST.get('custom_name', '').strip()
        notes = request.POST.get('notes', '').strip()
        if lab_test_id or custom_name:
            lab_test = LabTest.objects.filter(id=lab_test_id).first() if lab_test_id else None
            PatientBloodTest.objects.create(
                patient=patient, lab_test=lab_test,
                custom_name='' if lab_test else custom_name, notes=notes,
                recorded_by=request.user,
            )
    return _physio_tab_redirect(patient_id, 'blood_tests')


@login_required
def physio_bloodtest_delete(request, patient_id, bloodtest_id):
    if request.method == "POST":
        PatientBloodTest.objects.filter(id=bloodtest_id, patient_id=patient_id).delete()
    return _physio_tab_redirect(patient_id, 'blood_tests')


@login_required
def physio_aid_add(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    if request.method == "POST":
        product_id = request.POST.get('product_id', '').strip()
        custom_name = request.POST.get('custom_name', '').strip()
        notes = request.POST.get('notes', '').strip()
        if product_id or custom_name:
            product = Product.objects.filter(id=product_id).first() if product_id else None
            PatientAid.objects.create(
                patient=patient, product=product,
                custom_name='' if product else custom_name, notes=notes,
                recorded_by=request.user,
            )
    return _physio_tab_redirect(patient_id, 'surgicare')


@login_required
def physio_aid_delete(request, patient_id, aid_id):
    if request.method == "POST":
        PatientAid.objects.filter(id=aid_id, patient_id=patient_id).delete()
    return _physio_tab_redirect(patient_id, 'surgicare')


@login_required
def physio_assessment_entry_add(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    if request.method == "POST":
        reference_id = request.POST.get('reference_id', '').strip()
        notes = request.POST.get('notes', '').strip()
        reference = SpecialTestReference.objects.filter(id=reference_id, is_active=True).first()
        if reference:
            PatientAssessmentEntry.objects.get_or_create(
                patient=patient, reference=reference,
                defaults={'notes': notes, 'recorded_by': request.user},
            )
    return _physio_tab_redirect(patient_id, 'physiotherapy', 'assessment')


@login_required
def physio_assessment_entry_delete(request, patient_id, entry_id):
    if request.method == "POST":
        PatientAssessmentEntry.objects.filter(id=entry_id, patient_id=patient_id).delete()
    return _physio_tab_redirect(patient_id, 'physiotherapy', 'assessment')


@login_required
def physio_diet_add(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    if request.method == "POST":
        meal_time = request.POST.get('meal_time', '').strip()
        food_item = request.POST.get('food_item', '').strip()
        notes = request.POST.get('notes', '').strip()
        if meal_time in dict(PatientDietEntry.MEAL_CHOICES) and food_item:
            PatientDietEntry.objects.create(
                patient=patient, meal_time=meal_time, food_item=food_item, notes=notes,
                recorded_by=request.user,
            )
    return _physio_tab_redirect(patient_id, 'diet')


@login_required
def physio_diet_delete(request, patient_id, diet_id):
    if request.method == "POST":
        PatientDietEntry.objects.filter(id=diet_id, patient_id=patient_id).delete()
    return _physio_tab_redirect(patient_id, 'diet')


@login_required
def physio_consultation_add(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    if request.method == "POST":
        doctor_name = request.POST.get('doctor_name', '').strip()
        visit_date = parse_date(request.POST.get('visit_date', '').strip())
        notes = request.POST.get('notes', '').strip()
        follow_up_date = parse_date(request.POST.get('follow_up_date', '').strip())
        if doctor_name and visit_date:
            PatientConsultation.objects.create(
                patient=patient, doctor_name=doctor_name, visit_date=visit_date,
                notes=notes, follow_up_date=follow_up_date,
                recorded_by=request.user,
            )
    return _physio_tab_redirect(patient_id, 'consultation')


@login_required
def physio_consultation_delete(request, patient_id, consultation_id):
    if request.method == "POST":
        PatientConsultation.objects.filter(id=consultation_id, patient_id=patient_id).delete()
    return _physio_tab_redirect(patient_id, 'consultation')


@login_required
def physio_rx_add(request, patient_id):
    """Issues a new digital prescription -- unlike every other Medical
    Profile entry, there is no patient-facing equivalent of this view:
    only a physio/doctor can create an Rx."""
    patient = get_object_or_404(AddPatient, id=patient_id)
    if request.method == "POST":
        pharmacy_product_id = request.POST.get('pharmacy_product_id', '').strip()
        custom_name = request.POST.get('custom_name', '').strip()
        dosage = request.POST.get('dosage', '').strip()
        time_of_day = request.POST.get('time_of_day', '').strip()
        start_date = parse_date(request.POST.get('start_date', '').strip()) or date.today()
        duration_raw = request.POST.get('duration_days', '').strip()
        duration_days = int(duration_raw) if duration_raw.isdigit() else None
        notes = request.POST.get('notes', '').strip()
        if time_of_day in dict(Rx.TIME_CHOICES) and (pharmacy_product_id or custom_name):
            pharmacy_product = PharmacyProduct.objects.filter(id=pharmacy_product_id).first() if pharmacy_product_id else None
            Rx.objects.create(
                patient=patient, issued_by=request.user, pharmacy_product=pharmacy_product,
                custom_name='' if pharmacy_product else custom_name, dosage=dosage,
                time_of_day=time_of_day, start_date=start_date, duration_days=duration_days,
                notes=notes,
            )
    return _physio_tab_redirect(patient_id, 'medication')


@login_required
def physio_rx_status(request, patient_id, rx_id):
    if request.method == "POST":
        status = request.POST.get('status', '').strip()
        if status in dict(Rx.STATUS_CHOICES):
            Rx.objects.filter(id=rx_id, patient_id=patient_id).update(status=status)
    return _physio_tab_redirect(patient_id, 'medication')


@login_required
def physio_rx_delete(request, patient_id, rx_id):
    if request.method == "POST":
        Rx.objects.filter(id=rx_id, patient_id=patient_id).delete()
    return _physio_tab_redirect(patient_id, 'medication')