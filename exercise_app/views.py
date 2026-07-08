from django.shortcuts import render, get_object_or_404, redirect
from .models import SubRegion, ExerciseMain,Prescription,PrescriptionExercise
from django.http import JsonResponse
from personal_account.models import AddPatient
from datetime import datetime, timedelta,date
from django.utils import timezone   # Django's timezone has .now()
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max





# Create your views here.
def load_exercises(request,patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)  # single object

            # Get all sub-regions for the exercise dropdown
    sub_regions = SubRegion.objects.all()

    # If ?prescription_id=<id> is present, this page appends picked
    # exercises to that existing prescription instead of creating a new
    # one -- used by the "+ Add Exercise" link on the Track page.
    append_prescription = None
    prescription_id = request.GET.get('prescription_id')
    if prescription_id:
        append_prescription = Prescription.objects.filter(id=prescription_id, patient=patient).first()

    # Prepare context with both patient and exercise data
    context = {
        # Exercise information
        'patient': patient,
        'sub_regions': sub_regions,
        'append_prescription': append_prescription,
    }

    return render (request, 'exercise-selectable.html', context)


def get_exercises_by_subregion(request):
    sub_region_id = request.GET.get('sub_region_id') 
    if sub_region_id:
        exercises_qs = ExerciseMain.objects.filter(sub_region_fk_id=sub_region_id)
        exercises = exercises_qs.values(
            'id', 'exercise_name', 'exercise_type', 'difficulty_level',
            'default_sets', 'default_reps', 'hold_time_sec', 'exercise_description', 'exercise_url'
        )
        return JsonResponse({'exercises': list(exercises)})
    return JsonResponse({'exercises': []})


@csrf_exempt
@require_http_methods(["POST"])
def submit_prescription(request):
    try:
        data = json.loads(request.body)
        
        patient_id = data.get('patient_id')
        exercises_data = data.get('exercises', [])
        condition_label = data.get('condition_label', '').strip()
        # notes = data.get('notes', '')
        # start_date = data.get('start_date')
        # duration_days = data.get('duration_days', 30)
        
        # Validate required data
        if not patient_id:
            return JsonResponse({
                'success': False,
                'error': 'Patient ID is required'
            }, status=400)
        
        if not exercises_data:
            return JsonResponse({
                'success': False,
                'error': 'At least one exercise is required'
            }, status=400)
        
        # Get patient from sajhya_app
        try:
            patient = AddPatient.objects.get(id=patient_id)
        except AddPatient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Patient not found'
            }, status=404)
        
        # Parse dates
        # if start_date:
        #     start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        # else:
        #     start_date_obj = timezone.now().date()
        
        # end_date_obj = start_date_obj + timedelta(days=duration_days)
        
        # Create prescription
        prescription = Prescription.objects.create(
            patient=patient,
            condition_label=condition_label,
            # prescription_notes=notes,
            # start_date=start_date_obj,
            # end_date=end_date_obj,
            status='active',
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Add exercises to prescription with ordering
        for index, ex_data in enumerate(exercises_data):
            exercise_id = ex_data.get('id') or ex_data.get('exercise_id')
            
            # Try to get the actual Exercise object from exe_app
            exercise_obj = None
            try:
                exercise_obj = ExerciseMain.objects.get(id=exercise_id)
            except ExerciseMain.DoesNotExist:
                pass  # If exercise doesn't exist in library, still create prescription exercise with snapshot data
            
            PrescriptionExercise.objects.create(
                prescription=prescription,
                exercise=exercise_obj,
                exercise_id_in_library=exercise_id,
                exercise_name=ex_data.get('exercise_name', 'Unknown Exercise'),
                difficulty_level=ex_data.get('difficulty_level', 1),
                order=index,
                sets=exercise_obj.default_sets if exercise_obj else 3,
                reps=exercise_obj.default_reps if exercise_obj else 10,
                hold_time_sec=exercise_obj.hold_time_sec if exercise_obj else 0,
                rest_time_sec=exercise_obj.default_rest_time_sec if exercise_obj else 60,
                schedule_morning=ex_data.get('schedule_morning', True),
                schedule_day=ex_data.get('schedule_day', False),
                schedule_evening=ex_data.get('schedule_evening', False),
            )
        
        return JsonResponse({
            'success': True,
            'redirect_url': f'/detail-app/patient-exericse-status/{patient_id}/',  # Add this line
            'prescription_id': prescription.id,
            'message': f'Successfully prescribed {len(exercises_data)} exercises to {patient.patient_name}',
            'prescription': {
                'id': prescription.id,
                'total_exercises': prescription.get_total_exercises()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def add_exercises_to_prescription(request, prescription_id):
    try:
        prescription = Prescription.objects.get(id=prescription_id)
    except Prescription.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Prescription not found'}, status=404)

    try:
        data = json.loads(request.body)
        exercises_data = data.get('exercises', [])
        if not exercises_data:
            return JsonResponse({'success': False, 'error': 'At least one exercise is required'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

    max_order = prescription.exercises.aggregate(m=Max('order'))['m']
    next_order = 0 if max_order is None else max_order + 1

    for offset, ex_data in enumerate(exercises_data):
        exercise_id = ex_data.get('id') or ex_data.get('exercise_id')

        exercise_obj = None
        try:
            exercise_obj = ExerciseMain.objects.get(id=exercise_id)
        except ExerciseMain.DoesNotExist:
            pass

        PrescriptionExercise.objects.create(
            prescription=prescription,
            exercise=exercise_obj,
            exercise_id_in_library=exercise_id,
            exercise_name=ex_data.get('exercise_name', 'Unknown Exercise'),
            difficulty_level=ex_data.get('difficulty_level', 1),
            order=next_order + offset,
            sets=exercise_obj.default_sets if exercise_obj else 3,
            reps=exercise_obj.default_reps if exercise_obj else 10,
            hold_time_sec=exercise_obj.hold_time_sec if exercise_obj else 0,
            rest_time_sec=exercise_obj.default_rest_time_sec if exercise_obj else 60,
            schedule_morning=ex_data.get('schedule_morning', True),
            schedule_day=ex_data.get('schedule_day', False),
            schedule_evening=ex_data.get('schedule_evening', False),
        )

    return JsonResponse({
        'success': True,
        'redirect_url': f'/detail-app/patient-exericse-status/{prescription.patient_id}/',
        'prescription_id': prescription.id,
        'message': f'Added {len(exercises_data)} exercise(s) to the prescription',
    })


def prescription_exercise_details(request):
    return render (request, 'prescription-exercise-details.html')


def patient_prescriptions_view(request, patient_id):
    """View to display all prescriptions for a patient"""
    patient = get_object_or_404(AddPatient, id=patient_id)
    prescriptions = Prescription.objects.filter(patient=patient).order_by('-created_at')
    
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
        progress_percentage = (completed_exercises / total_exercises * 100) if total_exercises > 0 else 0
        
        # Check if prescription is active
        today = date.today()
        is_active = (prescription.status == 'active')
        
        prescriptions_data.append({
            'prescription': prescription,
            'exercises': exercises,
            'total_exercises': total_exercises,
            'completed_exercises': completed_exercises,
            'progress_percentage': round(progress_percentage, 1),
            'is_active': is_active,
          
        })
    
    context = {
        'patient': patient,
        'prescriptions': prescriptions_data,
        'total_prescriptions': total_prescriptions,
        'active_prescriptions': active_prescriptions,
        'completed_prescriptions': completed_prescriptions,
        'today': date.today(),
    }
    
    return render(request, 'exercise/patient_prescriptions.html', context)


def session_detail(request):
    return render (request, 'session-details.html')




def add_edit_exercise(request, patient_id):
    patient = get_object_or_404(AddPatient, id=patient_id)

    # 1. Get the most recent prescription for this patient (latest created_at)
    latest_prescription = Prescription.objects.filter(patient=patient).order_by('-created_at').first()

    # 2. Fetch exercises only if a prescription exists
    exercises = []
    if latest_prescription:
        # If you have a ManyToMany field named 'exercises' on Prescription:
        exercises = latest_prescription.exercises.all().order_by('order')
        print (f"{exercises}")
        
    return render(request, 'addexercise/add-exercise.html', {'exercises': exercises})




@login_required
def reassign_exercise(request, patient_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        patient = AddPatient.objects.get(id=patient_id)
    except AddPatient.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Patient not found'}, status=404)

    # Get the latest prescription for this patient
    latest = Prescription.objects.filter(patient=patient).order_by('-created_at').first()
    if not latest:
        return JsonResponse({
            'success': False,
            'error': 'No previous prescription found to copy from.'
        }, status=400)

    # Create a new prescription (copy status and user, or set as you wish)
    with transaction.atomic():
        new_prescription = Prescription.objects.create(
            patient=patient,
            condition_label=latest.condition_label,
            status='active',                     # or copy from latest.status
            created_by=request.user if request.user.is_authenticated else None
        )

        # Copy all PrescriptionExercise entries from the latest prescription
        for old_pe in latest.exercises.all().order_by('order'):
            PrescriptionExercise.objects.create(
                prescription=new_prescription,
                exercise=old_pe.exercise,
                exercise_id_in_library=old_pe.exercise_id_in_library,
                exercise_name=old_pe.exercise_name,
                difficulty_level=old_pe.difficulty_level,
                order=old_pe.order,
                sets=old_pe.sets,
                reps=old_pe.reps,
                hold_time_sec=old_pe.hold_time_sec,
                rest_time_sec=old_pe.rest_time_sec,
                schedule_morning=old_pe.schedule_morning,
                schedule_day=old_pe.schedule_day,
                schedule_evening=old_pe.schedule_evening,
            )


    return redirect(f'/detail-app/patient-exericse-status/{patient_id}/')