from django.shortcuts import render, get_object_or_404
from datetime import date
from personal_account.models import AddPatient, Clinic
from exercise_app.models import Prescription, PrescriptionExercise, ExerciseFeedback
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from prescription_app.models import TreatmentSession
from marketplace_app.views import get_recommended_for_diagnosis
from marketplace_app.models import PatientProductRecommendation


# Create your views here.
def patient_detail(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)
    sessions = TreatmentSession.objects.filter(patient_id=patient_id).only(
        'session_date', 'session_number', 'treatment_response'
    )
    manual_recs = (
        PatientProductRecommendation.objects.filter(patient=patient)
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
        'start_date': latest_prescription.start_date.isoformat(),
        'end_date': latest_prescription.end_date.isoformat(),
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