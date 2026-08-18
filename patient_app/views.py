from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Prefetch, F
from personal_account.models import AddPatient, ActivationCard, PatientPhysioPairing, get_nepal_time
from exercise_app.models import Prescription, PrescriptionExercise, ExerciseFeedback
from marketplace_app.models import Category, Product, ProductVariant, Order, OrderItem, Commission, CommissionRate, PatientProductRecommendation
from lab_app.models import LabTest, LabTestRequest, LabTestRequestItem
from marketplace_app.views import get_recommended_for_diagnosis
from marketplace_app.templatetags.marketplace_extras import CATEGORY_ICON_IMAGES
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.db import transaction
import json
import logging
from datetime import timedelta
from decimal import Decimal
from urllib.parse import quote
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.hashers import make_password, check_password
from .models import PushSubscription, AppOpenEvent, VideoClickEvent

logger = logging.getLogger(__name__)


def _activation_status(patient):
    active = patient.is_activation_active
    days_remaining = (patient.activation_expires_at - get_nepal_time()).days if active else None
    return {
        'activation_active': active,
        'activation_expires_at': patient.activation_expires_at.isoformat() if patient.activation_expires_at else None,
        'activation_days_remaining': days_remaining,
    }


def patient_api_me(request):
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        patient = AddPatient.objects.get(id=patient_id)
        # Session outliving a deletion (e.g. a second device): report signed out.
        if patient.is_deleted:
            return JsonResponse({'error': 'Not authenticated'}, status=401)

        latest_prescription = Prescription.objects.filter(patient=patient).order_by('-created_at').first()
        prescription_data = None
        if latest_prescription:
            through_instances = latest_prescription.exercises.all().order_by('order')
            status = getattr(latest_prescription, 'status', 'active')
            notes = getattr(latest_prescription, 'prescription_notes', None) or getattr(latest_prescription, 'notes', None)
            prescription_data = {
                'id': latest_prescription.id,
                'created_at': latest_prescription.created_at.isoformat() if latest_prescription.created_at else '',
                'status': status,
                'prescription_notes': notes,
                'exercises': [
                    {
                        'id': ti.id,
                        'exercise_name': ti.exercise.exercise_name,
                        'exercise_url': request.build_absolute_uri(ti.exercise.exercise_url) if ti.exercise.exercise_url else None,
                        'youtube_url': ti.exercise.youtube_url if ti.exercise else None,
                        'sets': ti.sets,
                        'reps': ti.reps,
                        'hold_time_sec': ti.hold_time_sec,
                        'rest_time_sec': ti.rest_time_sec,
                        'schedule_morning': ti.schedule_morning,
                        'schedule_day': ti.schedule_day,
                        'schedule_evening': ti.schedule_evening,
                        'is_completed': ti.is_completed,
                        'description': ti.exercise.exercise_description if ti.exercise else '',
                        'description_nepali': ti.exercise.exercise_description_nepali if ti.exercise else '',
                        'step_images': [
                            {
                                'order': si.order,
                                'image_url': request.build_absolute_uri(si.image_url) if si.image_url else None,
                                'label': si.label,
                            } for si in ti.exercise.step_images.all()
                        ] if ti.exercise else [],
                    } for ti in through_instances
                ]
            }
        return JsonResponse({
            'success': True,
            'patient_id': patient.id,
            'patient_name': getattr(patient, 'patient_name', 'Patient'),
            'patient_code': patient.patient_code,
            'diagnosis': patient.patient_diagnosis or 'Not specified',
            'latest_prescription': prescription_data,
            **_activation_status(patient),
        })
    except AddPatient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)
@ensure_csrf_cookie
def csrf_token_view(request):
    return JsonResponse({'detail': 'CSRF cookie set'})

def patient_login(request):
    # If the browser sends a POST request (user clicked the button)
    if request.method == "POST":
        patient_code = request.POST.get('username')
        pin_input = request.POST.get('password')
        
        try:
            patient = AddPatient.objects.get(patient_code=patient_code)
            
            # FOR INTERNAL TESTING ONLY: Plain text comparison
            # ⚠️ REPLACE THIS WITH HASHED PIN IN PRODUCTION
            if patient.patient_contact == pin_input:
                # Store the patient's ID in the session (this logs them in)
                request.session['patient_id'] = patient.id
                
                # ✅ Simply redirect to the dashboard
                # The dashboard will handle fetching the prescription
                return redirect('patient-dashboard')
            else:
                return render(request, 'patient-login.html', {'error': 'Invalid credentials'})
                
        except AddPatient.DoesNotExist:
            return render(request, 'patient-login.html', {'error': 'Invalid credentials'})
    
    # If GET request, show the login form
    return render(request, 'patient-login.html')
    

# ==================== CUSTOM DECORATOR ====================

# Custom decorator to check if patient is logged in
def patient_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('patient_id'):
            return redirect('patient-login')
        return view_func(request, *args, **kwargs)
    return wrapper
# ==================== WEB DASHBOARD ====================

@patient_login_required  # ✅ This checks your custom session
def patient_dashboard(request):
    # Get the logged-in patient
    patient_id = request.session.get('patient_id')
    patient = get_object_or_404(AddPatient, id=patient_id)
    
    # ✅ Fetch the latest prescription HERE (not in login view)
    latest_prescription = Prescription.objects.filter(
        patient=patient
    ).order_by('-created_at').first()
    
    # exercises = []
    # exercises = latest_prescription.exercises.all().order_by('order')
        # ✅ SAFE CHECK: Initialize exercises as empty list if no prescription
    exercises = []
    if latest_prescription:
        exercises = latest_prescription.exercises.all().order_by('order')
    # print (exercises)
    # Physio hand-picked products
    manual_recs = (
        PatientProductRecommendation.objects.filter(patient=patient)
        .select_related('product', 'product__category')
    )
    manual_ids = list(manual_recs.values_list('product_id', flat=True))
    # Auto-suggested from diagnosis (exclude already-picked)
    auto_recs, matched_label = get_recommended_for_diagnosis(patient.patient_diagnosis)
    auto_recs = auto_recs.exclude(id__in=manual_ids).select_related('category')[:4]

    context = {
        'patient': patient,
        'latest_prescription': latest_prescription,
        'exercises': exercises,
        'manual_recs': manual_recs,
        'auto_recs': auto_recs,
        'matched_label': matched_label,
        'vapid_public_key': settings.VAPID_PUBLIC_KEY,
    }

    return render(request, 'patient-dashboard-image.html', context)


def add_recs_to_cart(request):
    """Add all recommended products for the logged-in patient into the session cart."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient-login')
    patient = get_object_or_404(AddPatient, id=patient_id)

    from marketplace_app.views import _get_cart, _save_cart
    cart = _get_cart(request)

    manual_recs = PatientProductRecommendation.objects.filter(patient=patient).select_related('product', 'product__category')
    manual_ids = []
    for rec in manual_recs:
        p = rec.product
        if not p.in_stock:
            continue
        manual_ids.append(p.id)
        pid = str(p.id)
        if pid not in cart:
            cart[pid] = {
                'name': p.name,
                'price': str(p.price),
                'quantity': 1,
                'unit': p.unit,
                'category': p.category.name if p.category else '',
            }

    auto_recs, _ = get_recommended_for_diagnosis(patient.patient_diagnosis)
    for p in auto_recs.exclude(id__in=manual_ids).select_related('category'):
        if not p.in_stock:
            continue
        pid = str(p.id)
        if pid not in cart:
            cart[pid] = {
                'name': p.name,
                'price': str(p.price),
                'quantity': 1,
                'unit': p.unit,
                'category': p.category.name if p.category else '',
            }

    _save_cart(request, cart)
    return redirect('view-cart')


# ==================== MOBILE API LOGIN ====================

@csrf_exempt
@require_http_methods(["POST"])
def patient_api_login(request):
    try:
        data = json.loads(request.body)
        patient_code = data.get('username', '').strip()
        secret = data.get('password', '').strip()

        if not patient_code or not secret:
            return JsonResponse({'success': False, 'error': 'Patient Code and password are required'}, status=400)

        patient = AddPatient.objects.filter(patient_code=patient_code).first()
        if not patient:
            return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

        # A deleted account keeps its row (anonymised) so clinical records stay
        # linked, so it must be refused here explicitly. Same generic message as
        # a bad password -- whether a code once existed is not worth disclosing.
        if patient.is_deleted:
            return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

        if patient.password:
            # Self-registered patient: verify the hashed password they chose.
            valid = check_password(secret, patient.password)
        else:
            # Physio-created patient: legacy patient_code + phone-as-PIN check.
            valid = patient.patient_contact == secret
        if not valid:
            return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

        request.session['patient_id'] = patient.id

        # --- Fetch latest prescription ---
        latest_prescription = Prescription.objects.filter(patient=patient).order_by('-created_at').first()
        prescription_data = None
        if latest_prescription:
            through_instances = latest_prescription.exercises.all().order_by('order')

            status = getattr(latest_prescription, 'status', 'active')
            notes = getattr(latest_prescription, 'prescription_notes', None) or getattr(latest_prescription, 'notes', None)

            prescription_data = {
                'id': latest_prescription.id,
                'created_at': latest_prescription.created_at.isoformat() if latest_prescription.created_at else '',
                'status': status,
                'prescription_notes': notes,
                'exercises': [
                    {
                        'id': ti.id,
                        'exercise_name': ti.exercise.exercise_name,
                        'exercise_url': request.build_absolute_uri(ti.exercise.exercise_url) if ti.exercise.exercise_url else None,
                        'youtube_url': ti.exercise.youtube_url if ti.exercise else None,
                        'sets': ti.sets,
                        'reps': ti.reps,
                        'hold_time_sec': ti.hold_time_sec,
                        'rest_time_sec': ti.rest_time_sec,
                        'schedule_morning': ti.schedule_morning,
                        'schedule_day': ti.schedule_day,
                        'schedule_evening': ti.schedule_evening,
                        'is_completed': ti.is_completed,
                        'description': ti.exercise.exercise_description if ti.exercise else '',
                        'description_nepali': ti.exercise.exercise_description_nepali if ti.exercise else '',
                        'step_images': [
                            {
                                'order': si.order,
                                'image_url': request.build_absolute_uri(si.image_url) if si.image_url else None,
                                'label': si.label,
                            } for si in ti.exercise.step_images.all()
                        ] if ti.exercise else [],
                    } for ti in through_instances
                ]
            }

        # Build response
        patient_name = getattr(patient, 'patient_name', 'Patient')
        diagnosis = patient.patient_diagnosis or 'Not specified'
        response_data = {
            'success': True,
            'patient_id': patient.id,
            'patient_name': patient_name,
            'patient_code': patient.patient_code,
            'diagnosis': diagnosis,
            'latest_prescription': prescription_data,
            **_activation_status(patient),
            'message': 'Login successful'
        }

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except AddPatient.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(traceback.format_exc())
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_qr_login(request):
    try:
        data = json.loads(request.body)
        qr_token = data.get('qr_token', '').strip()

        if not qr_token:
            return JsonResponse({'success': False, 'error': 'QR token is required'}, status=400)

        patient = AddPatient.objects.get(qr_token=qr_token)
        # Deletion clears qr_token, so a deleted patient should not be reachable
        # here at all; checked anyway so a re-issued token can never resurrect a
        # deleted account.
        if patient.is_deleted:
            return JsonResponse({'success': False, 'error': 'Invalid QR code'}, status=401)

        request.session['patient_id'] = patient.id

        latest_prescription = Prescription.objects.filter(patient=patient).order_by('-created_at').first()
        prescription_data = None
        if latest_prescription:
            through_instances = latest_prescription.exercises.all().order_by('order')
            status = getattr(latest_prescription, 'status', 'active')
            notes = getattr(latest_prescription, 'prescription_notes', None) or getattr(latest_prescription, 'notes', None)
            prescription_data = {
                'id': latest_prescription.id,
                'created_at': latest_prescription.created_at.isoformat() if latest_prescription.created_at else '',
                'status': status,
                'prescription_notes': notes,
                'exercises': [
                    {
                        'id': ti.id,
                        'exercise_name': ti.exercise.exercise_name,
                        'exercise_url': request.build_absolute_uri(ti.exercise.exercise_url) if ti.exercise.exercise_url else None,
                        'youtube_url': ti.exercise.youtube_url if ti.exercise else None,
                        'sets': ti.sets,
                        'reps': ti.reps,
                        'hold_time_sec': ti.hold_time_sec,
                        'rest_time_sec': ti.rest_time_sec,
                        'schedule_morning': ti.schedule_morning,
                        'schedule_day': ti.schedule_day,
                        'schedule_evening': ti.schedule_evening,
                        'is_completed': ti.is_completed,
                        'description': ti.exercise.exercise_description if ti.exercise else '',
                        'description_nepali': ti.exercise.exercise_description_nepali if ti.exercise else '',
                        'step_images': [
                            {
                                'order': si.order,
                                'image_url': request.build_absolute_uri(si.image_url) if si.image_url else None,
                                'label': si.label,
                            } for si in ti.exercise.step_images.all()
                        ] if ti.exercise else [],
                    } for ti in through_instances
                ]
            }

        return JsonResponse({
            'success': True,
            'patient_id': patient.id,
            'patient_name': getattr(patient, 'patient_name', 'Patient'),
            'patient_code': patient.patient_code,
            'diagnosis': patient.patient_diagnosis or 'Not specified',
            'latest_prescription': prescription_data,
            **_activation_status(patient),
            'message': 'QR login successful',
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except AddPatient.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid QR code'}, status=401)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_signup(request):
    """Lets a patient create their own account from the app, with no physio
    involved yet -- they land unassigned and pair with a physio afterward via
    patient_api_pair_physio (see AddPatient.created_by docstring). Their
    login identifier is the auto-generated patient_code (same as
    physio-created patients); what's different is they choose their own
    password instead of using their phone number as the PIN."""
    try:
        data = json.loads(request.body)
        patient_name = data.get('patient_name', '').strip()
        password = data.get('password', '')

        if not patient_name or not password:
            return JsonResponse({'success': False, 'error': 'Name and password are required'}, status=400)
        if len(password) < 6:
            return JsonResponse({'success': False, 'error': 'Password must be at least 6 characters'}, status=400)

        patient = AddPatient.objects.create(
            patient_name=patient_name,
            patient_contact='',
            patient_diagnosis='Not specified',
            password=make_password(password),
        )
        request.session['patient_id'] = patient.id

        return JsonResponse({
            'success': True,
            'patient_id': patient.id,
            'patient_name': patient.patient_name,
            'patient_code': patient.patient_code,
            'diagnosis': patient.patient_diagnosis,
            'latest_prescription': None,
            **_activation_status(patient),
            'message': 'Account created successfully',
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_activate(request):
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    try:
        patient = AddPatient.objects.get(id=patient_id)
    except AddPatient.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Patient not found'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    code = data.get('code', '').strip().upper()
    if not code:
        return JsonResponse({'success': False, 'error': 'Activation code is required'}, status=400)

    try:
        card = ActivationCard.objects.get(code=code)
    except ActivationCard.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid activation code'}, status=404)

    if card.is_used:
        return JsonResponse({'success': False, 'error': 'This activation code has already been used'}, status=400)

    now = get_nepal_time()
    # If the patient still has time left, extend from that point rather than
    # from now, so redeeming early never loses days already paid for.
    base = patient.activation_expires_at if patient.activation_expires_at and patient.activation_expires_at > now else now
    patient.activation_expires_at = base + timedelta(days=card.duration_days)
    patient.save(update_fields=['activation_expires_at'])

    card.is_used = True
    card.used_by = patient
    card.used_at = now
    card.save(update_fields=['is_used', 'used_by', 'used_at'])

    return JsonResponse({
        'success': True,
        'message': 'Activation successful',
        **_activation_status(patient),
    })


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_pair_physio(request):
    """Scanning a physio's pairing QR lands here: links this patient to that
    physio via PatientPhysioPairing (source='self_registered_qr'), the
    counterpart to the physio-side pairing QR display in physio_api_app."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    try:
        patient = AddPatient.objects.get(id=patient_id)
    except AddPatient.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Patient not found'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    pairing_token = data.get('pairing_token', '').strip()
    if not pairing_token:
        return JsonResponse({'success': False, 'error': 'Pairing code is required'}, status=400)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        physio = User.objects.get(pairing_token=pairing_token)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid pairing code'}, status=404)

    pairing, created = PatientPhysioPairing.objects.get_or_create(
        patient=patient, physio=physio,
        defaults={'source': 'self_registered_qr'},
    )

    return JsonResponse({
        'success': True,
        'physio_name': physio.get_full_name() or physio.username,
        'already_paired': not created,
    })


@csrf_exempt
@require_http_methods(["POST"])
def submit_exercise_feedback(request, exercise_id):
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    try:
        exercise = PrescriptionExercise.objects.select_related('prescription__patient').get(id=exercise_id)

        if exercise.prescription.patient.id != patient_id:
            return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

        data = json.loads(request.body)
        feedback_type = data.get('feedback_type', '').strip()
        note = data.get('note', '').strip()

        valid_types = [c[0] for c in ExerciseFeedback.FEEDBACK_CHOICES]
        if feedback_type not in valid_types:
            return JsonResponse({'success': False, 'error': 'Invalid feedback type'}, status=400)

        ExerciseFeedback.objects.create(
            prescription_exercise=exercise,
            feedback_type=feedback_type,
            note=note,
        )

        return JsonResponse({'success': True})

    except PrescriptionExercise.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Exercise not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== ENGAGEMENT TRACKING ====================
# "Completed" adherence data turned out to badly under-report real usage
# (patients open the app and watch the exercise without ever tapping the
# done button). These two pings give a second, independent read on actual
# engagement -- did the app get opened today, did the video get watched --
# without relying on the patient to self-report anything.

@csrf_exempt
@require_http_methods(["POST"])
def patient_api_ping_open(request):
    """Fire-and-forget: called once when the dashboard loads. Upserts a
    single row per patient per calendar day, so repeat pings the same day
    (backgrounding/resuming the app) just bump a counter instead of
    growing the table -- keeps this a clean daily-active-patient signal."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    try:
        patient = AddPatient.objects.get(id=patient_id, is_deleted=False)
    except AddPatient.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    today = get_nepal_time().date()
    event, created = AppOpenEvent.objects.get_or_create(
        patient=patient, opened_on=today,
    )
    if not created:
        event.ping_count = F('ping_count') + 1
        event.save(update_fields=['ping_count'])

    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def submit_video_click(request, exercise_id):
    """Fire-and-forget: called right before the app opens an exercise's
    YouTube link. exercise_id is the PrescriptionExercise id, same as the
    feedback endpoint above -- it's what the patient actually saw, not the
    library exercise, so it stays meaningful even if the library entry
    changes later."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    try:
        exercise = PrescriptionExercise.objects.select_related('prescription__patient').get(id=exercise_id)

        if exercise.prescription.patient.id != patient_id:
            return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

        VideoClickEvent.objects.create(
            prescription_exercise=exercise,
            exercise_id_in_library=exercise.exercise_id_in_library,
            exercise_name=exercise.exercise_name,
        )

        return JsonResponse({'success': True})

    except PrescriptionExercise.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Exercise not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== LOGOUT ====================

@csrf_exempt
@require_http_methods(['POST'])
def patient_api_logout(request):
    request.session.flush()
    return JsonResponse({'success': True})


def _purge_patient_personal_data(patient):
    """Erase everything that identifies `patient`, keeping the records the
    practice has to retain. Shared by the in-app and web deletion routes so the
    two cannot drift apart. Caller wraps this in a transaction.
    """
    PushSubscription.objects.filter(patient=patient).delete()
    PatientPhysioPairing.objects.filter(patient=patient).delete()
    PatientProductRecommendation.objects.filter(patient=patient).delete()

    # Marketplace orders carry a delivery name, phone and address, and are
    # linked to the patient only by the synthetic {patient_code}@sajhya.local
    # address. The order rows themselves stay (they back order history,
    # supplier fulfilment and physio commission accounting) but the delivery
    # details are personal data and are cleared. customer_email is kept as the
    # link key; once the patient is anonymised it identifies nobody.
    Order.objects.filter(
        customer_email=f'{patient.patient_code}@sajhya.local'
    ).update(
        customer_name='Deleted patient',
        customer_phone='',
        delivery_address='',
        notes='',
    )

    patient.anonymise_for_deletion()


@csrf_exempt
@require_http_methods(['POST'])
def patient_api_delete_account(request):
    """Delete the signed-in patient's account.

    Google Play requires an in-app deletion path for any app that offers
    account creation, so the patient app calls this from
    Dashboard > overflow > Delete my account.

    The AddPatient row is anonymised rather than dropped. Deleting it would
    cascade into prescriptions, exercise feedback, physio session notes and
    visit notes -- clinical records the practice is required to retain -- and
    would orphan marketplace orders and the physio commissions calculated from
    them. Instead every identifying field is cleared (see
    AddPatient.anonymise_for_deletion) and the app-side personal data is
    deleted outright:

      * push subscriptions   -- device endpoints, directly identifying
      * physio pairings      -- who was treating this person
      * product recommendations -- inferred from their diagnosis
      * the session cart     -- lives in the session, dropped with the flush

    What survives is de-identified: a patient_code with no name, contact,
    password or QR token attached, plus the clinical and financial history
    hanging off it. Retention must be disclosed in the privacy policy for the
    Play Data Safety declaration.
    """
    patient, err = _patient_required(request)
    if err:
        return err

    try:
        with transaction.atomic():
            _purge_patient_personal_data(patient)
    except Exception:
        logger.exception('Account deletion failed for patient id=%s', patient.id)
        return JsonResponse(
            {'success': False, 'error': 'Could not delete account. Please try again.'},
            status=500,
        )

    # Only after the data is gone, so a failure above leaves the patient signed
    # in and able to retry rather than locked out of a half-deleted account.
    request.session.flush()
    return JsonResponse({'success': True})


@require_http_methods(['GET'])
def patient_privacy_policy(request):
    """Public privacy policy for the Sajhya patient app.

    Google Play requires a reachable policy URL on the store listing and in the
    Data Safety form; for an app handling health data it is checked closely.
    The content must stay in step with what the code actually does -- notably
    _purge_patient_personal_data() and the retention it describes.
    """
    return render(request, 'patient-privacy-policy.html', {
        'last_updated': '10 August 2026',
        'contact_email': settings.PRIVACY_CONTACT_EMAIL,
    })


@require_http_methods(['GET', 'POST'])
def patient_delete_account_web(request):
    """Browser-based account deletion, no app install required.

    Google Play requires a deletion route reachable from outside the app; its
    URL is submitted with the Data Safety form. Authenticates with the same
    credentials as the app so a deletion request cannot be forged from a
    patient code alone -- those are printed on cards and are not secret.
    """
    if request.method == 'GET':
        return render(request, 'patient-delete-account.html')

    patient_code = (request.POST.get('patient_code') or '').strip()
    secret = (request.POST.get('password') or '').strip()
    confirm = (request.POST.get('confirm') or '').strip().upper()

    if confirm != 'DELETE':
        return render(request, 'patient-delete-account.html', {
            'error': 'Type DELETE in the confirmation box to continue.',
            'patient_code': patient_code,
        })

    patient = AddPatient.objects.filter(patient_code=patient_code).first()
    valid = False
    if patient and not patient.is_deleted:
        if patient.password:
            valid = check_password(secret, patient.password)
        else:
            valid = patient.patient_contact == secret

    if not valid:
        return render(request, 'patient-delete-account.html', {
            'error': 'Invalid Patient Code or PIN/password.',
            'patient_code': patient_code,
        })

    try:
        with transaction.atomic():
            _purge_patient_personal_data(patient)
    except Exception:
        logger.exception('Web account deletion failed for patient id=%s', patient.id)
        return render(request, 'patient-delete-account.html', {
            'error': 'Something went wrong. Please try again or contact support.',
            'patient_code': patient_code,
        })

    request.session.flush()
    return render(request, 'patient-delete-account.html', {'deleted': True})


# ==================== PUSH NOTIFICATIONS ====================

def patient_service_worker(request):
    """Minimal service worker: no offline caching, just enough to receive
    and display a Web Push notification and focus/open the dashboard when
    it's tapped."""
    script = """
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

self.addEventListener('push', (event) => {
    let payload = { title: 'Sajhya', body: 'You have a new notification.' };
    if (event.data) {
        try { payload = event.data.json(); } catch (e) {}
    }
    event.waitUntil(
        self.registration.showNotification(payload.title, {
            body: payload.body,
            icon: '/static/icons/ward-icon-192.png',
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
            for (const client of windowClients) {
                if (client.url.includes('/patient-app/') && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow('/patient-app/patient-dashboard/');
            }
        })
    );
});
"""
    return HttpResponse(script, content_type='application/javascript')


@csrf_exempt
@require_http_methods(['POST'])
def patient_api_push_subscribe(request):
    patient, err = _patient_required(request)
    if err:
        return err

    try:
        data = json.loads(request.body)
        endpoint = data['endpoint']
        p256dh = data['keys']['p256dh']
        auth = data['keys']['auth']
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'success': False, 'error': 'Invalid subscription payload'}, status=400)

    PushSubscription.objects.update_or_create(
        patient=patient,
        endpoint=endpoint,
        defaults={'p256dh': p256dh, 'auth': auth},
    )
    return JsonResponse({'success': True})


# ==================== MARKETPLACE API ====================

def _patient_required(request):
    pid = request.session.get('patient_id')
    if not pid:
        return None, JsonResponse({'error': 'Not authenticated'}, status=401)
    try:
        patient = AddPatient.objects.get(id=pid)
    except AddPatient.DoesNotExist:
        return None, JsonResponse({'error': 'Patient not found'}, status=404)
    # Covers a session still live on another device when the account was
    # deleted; treated as signed out so the app returns to the login screen.
    if patient.is_deleted:
        return None, JsonResponse({'error': 'Not authenticated'}, status=401)
    return patient, None


def _image_url(request, image_path):
    if not image_path:
        return None
    encoded = quote(image_path, safe='/')
    return request.build_absolute_uri(f'{settings.STATIC_URL}{encoded}')


def _category_icon_url(request, category_name):
    """Same CATEGORY_ICON_IMAGES lookup the web marketplace template uses
    (marketplace_app.templatetags.marketplace_extras.category_icon_image),
    exposed here so the app can show the same logo instead of the icon
    emoji. None if that category has no photo yet -- app falls back to
    the emoji, same as the template does."""
    filename = CATEGORY_ICON_IMAGES.get(category_name)
    if not filename:
        return None
    return _image_url(request, f'categorized_product/category_icons/{filename}')


def _variants_prefetch():
    """Shared Prefetch for patient_api_products/patient_api_pharmacy_products --
    one query for all products' variants instead of one per product."""
    return Prefetch(
        'variants',
        queryset=ProductVariant.objects.filter(in_stock=True).order_by('sort_order', 'id'),
        to_attr='in_stock_variants',
    )


def _product_variants(request, product):
    """Serialize a product's in-stock variants, falling back to the parent
    product's photo when a variant doesn't have its own. Expects
    `in_stock_variants` to be prefetched via _variants_prefetch() on the
    queryset; falls back to a fresh query if it wasn't."""
    variants = getattr(product, 'in_stock_variants', None)
    if variants is None:
        variants = product.variants.filter(in_stock=True).order_by('sort_order', 'id')
    return [
        {
            'id': v.id,
            'label': v.label,
            'price': str(v.price),
            'in_stock': v.in_stock,
            'image_url': _image_url(request, v.image) if v.image else _image_url(request, product.image),
        }
        for v in variants
    ]


def _get_patient_cart(request):
    return request.session.get('patient_cart', {})


def _save_patient_cart(request, cart):
    request.session['patient_cart'] = cart
    request.session.modified = True


def _parse_cart_key(key):
    """Cart dict keys are 'product_id' or 'product_id:variant_id'."""
    if ':' in key:
        pid_str, vid_str = key.split(':', 1)
        return int(pid_str), int(vid_str)
    return int(key), None


def patient_api_categories(request):
    patient, err = _patient_required(request)
    if err:
        return err
    # Pharmacy is a separate section (see patient_api_pharmacy_products) --
    # never listed as a Marketplace category.
    cats = Category.objects.exclude(name='Pharmacy').order_by('id')
    return JsonResponse({'categories': [
        {'id': c.id, 'name': c.name, 'icon': c.icon, 'icon_url': _category_icon_url(request, c.name)}
        for c in cats
    ]})


def patient_api_products(request):
    patient, err = _patient_required(request)
    if err:
        return err
    # Excluded unconditionally so this endpoint never returns Pharmacy
    # items, even if a caller passes its category id directly.
    qs = Product.objects.filter(in_stock=True).exclude(category__name='Pharmacy').select_related('category').prefetch_related(_variants_prefetch())
    cat_id = request.GET.get('category', '').strip()
    if cat_id:
        qs = qs.filter(category_id=cat_id)
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(name__icontains=search)
    data = [{
        'id': p.id,
        'name': p.name,
        'price': str(p.price),
        'unit': p.unit,
        'category': p.category.name if p.category else '',
        'image_url': _image_url(request, p.image),
        'description': p.description,
        'variants': _product_variants(request, p),
    } for p in qs]
    return JsonResponse({'products': data})


def patient_api_pharmacy_products(request):
    patient, err = _patient_required(request)
    if err:
        return err
    qs = Product.objects.filter(in_stock=True, category__name='Pharmacy').select_related('category').prefetch_related(_variants_prefetch())
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(name__icontains=search)
    data = [{
        'id': p.id,
        'name': p.name,
        'price': str(p.price),
        'unit': p.unit,
        'category': p.category.name if p.category else '',
        'image_url': _image_url(request, p.image),
        'description': p.description,
        'variants': _product_variants(request, p),
    } for p in qs]
    return JsonResponse({'products': data})


def patient_api_cart(request):
    patient, err = _patient_required(request)
    if err:
        return err
    cart = _get_patient_cart(request)
    items = []
    total = Decimal('0')
    for key, item in cart.items():
        pid, vid = _parse_cart_key(key)
        item_total = Decimal(str(item['price'])) * item['quantity']
        total += item_total
        items.append({
            'product_id': pid,
            'variant_id': vid,
            'variant_label': item.get('variant_label', ''),
            'name': item['name'],
            'price': str(item['price']),
            'quantity': item['quantity'],
            'unit': item.get('unit', ''),
            'image_url': item.get('image_url', ''),
            'item_total': str(item_total),
        })
    return JsonResponse({
        'items': items,
        'total': str(total),
        'count': sum(i['quantity'] for i in cart.values()),
    })


@csrf_exempt
@require_http_methods(['POST'])
def patient_api_cart_add(request, product_id):
    patient, err = _patient_required(request)
    if err:
        return err
    product = get_object_or_404(Product, id=product_id, in_stock=True)

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    variant = None
    variant_id = body.get('variant_id')
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product, in_stock=True)

    cart = _get_patient_cart(request)
    key = f'{product_id}:{variant.id}' if variant else str(product_id)
    if key in cart:
        cart[key]['quantity'] += 1
    else:
        cart[key] = {
            'name': product.name,
            'variant_label': variant.label if variant else '',
            'price': str(variant.price if variant else product.price),
            'quantity': 1,
            'unit': product.unit,
            'image_url': _image_url(request, (variant.image if variant and variant.image else product.image)),
        }
    _save_patient_cart(request, cart)
    return JsonResponse({'success': True, 'cart_count': sum(i['quantity'] for i in cart.values())})


@csrf_exempt
@require_http_methods(['POST'])
def patient_api_cart_update(request):
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
        pid = int(data['product_id'])
        vid = data.get('variant_id')
        qty = int(data.get('quantity', 0))
    except (json.JSONDecodeError, KeyError, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)
    key = f'{pid}:{vid}' if vid else str(pid)
    cart = _get_patient_cart(request)
    if key in cart:
        if qty <= 0:
            del cart[key]
        else:
            cart[key]['quantity'] = qty
    _save_patient_cart(request, cart)
    return JsonResponse({'success': True, 'cart_count': sum(i['quantity'] for i in cart.values())})


@csrf_exempt
@require_http_methods(['POST'])
def patient_api_order(request):
    patient, err = _patient_required(request)
    if err:
        return err
    cart = _get_patient_cart(request)
    if not cart:
        return JsonResponse({'error': 'Cart is empty'}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    delivery_address = data.get('delivery_address', '').strip()
    notes = data.get('notes', '').strip()
    # Self-registered patients have no patient_contact on file (that field
    # is no longer collected at signup), so the checkout form now asks for
    # a phone number directly; physio-created patients still have one
    # stored, which we fall back to if the app didn't send one.
    customer_phone = data.get('customer_phone', '').strip() or patient.patient_contact
    if not delivery_address:
        return JsonResponse({'error': 'Delivery address required'}, status=400)
    if not customer_phone:
        return JsonResponse({'error': 'Phone number required'}, status=400)

    total = sum(Decimal(str(item['price'])) * item['quantity'] for item in cart.values())

    order = Order.objects.create(
        customer_name=patient.patient_name,
        customer_email=f'{patient.patient_code}@sajhya.local',
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        notes=notes,
        total_amount=total,
    )
    for key, item in cart.items():
        pid, vid = _parse_cart_key(key)
        try:
            product = Product.objects.get(id=pid)
        except Product.DoesNotExist:
            product = None
        variant = ProductVariant.objects.filter(id=vid).first() if vid else None
        name = f"{item['name']} — {item['variant_label']}" if item.get('variant_label') else item['name']
        OrderItem.objects.create(
            order=order,
            product=product,
            variant=variant,
            product_name=name,
            quantity=item['quantity'],
            unit_price=Decimal(str(item['price'])),
        )

    # Auto-create commission for referring physio
    physio = patient.created_by
    if physio:
        rate = CommissionRate.get_rate_for_physio(physio)
        Commission.objects.create(
            order=order,
            physio=physio,
            patient_code=patient.patient_code,
            order_amount=total,
            commission_rate=rate,
            commission_amount=(total * rate / Decimal('100')).quantize(Decimal('0.01')),
        )

    _save_patient_cart(request, {})
    return JsonResponse({'success': True, 'order_number': order.order_number, 'total': str(total)})


def patient_api_orders(request):
    patient, err = _patient_required(request)
    if err:
        return err
    orders = Order.objects.filter(
        customer_email=f'{patient.patient_code}@sajhya.local'
    ).order_by('-created_at')[:20]
    data = [{
        'order_number': o.order_number,
        'total': str(o.total_amount),
        'status': o.status,
        'status_display': o.get_status_display(),
        'created_at': o.created_at.strftime('%d %b %Y'),
        'items_count': o.items.count(),
    } for o in orders]
    return JsonResponse({'orders': data})


# ==================== LAB SERVICE (Blood Investigation) ====================
# First real Services-tab feature -- Physiotherapy/Dental/Dietician/etc. are
# still "coming soon" placeholders in the app. Mirrors the marketplace
# order flow (patient submits, clinic processes) rather than adding a new
# shape of workflow.

@csrf_exempt
@require_http_methods(["GET"])
def patient_api_lab_tests(request):
    patient, err = _patient_required(request)
    if err:
        return err
    tests = LabTest.objects.filter(is_active=True)
    return JsonResponse({'lab_tests': [
        {
            'id': t.id,
            'name': t.name,
            'category': t.category,
            'category_display': t.get_category_display(),
            'price': str(t.price),
            'sample_type': t.sample_type,
            'prep_instructions': t.prep_instructions,
            'turnaround_time': t.turnaround_time,
        }
        for t in tests
    ]})


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_lab_request_create(request):
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    test_ids = data.get('test_ids') or []
    notes = data.get('notes', '').strip()
    if not test_ids:
        return JsonResponse({'error': 'Select at least one test'}, status=400)

    tests = list(LabTest.objects.filter(id__in=test_ids, is_active=True))
    if not tests:
        return JsonResponse({'error': 'No valid tests selected'}, status=400)

    total = sum((t.price for t in tests), Decimal('0'))

    lab_request = LabTestRequest.objects.create(
        patient=patient,
        notes=notes,
        total_amount=total,
    )
    for t in tests:
        LabTestRequestItem.objects.create(
            request=lab_request,
            lab_test=t,
            test_name=t.name,
            price=t.price,
        )

    return JsonResponse({
        'success': True,
        'request_number': lab_request.request_number,
        'total': str(lab_request.total_amount),
    }, status=201)


@csrf_exempt
@require_http_methods(["GET"])
def patient_api_lab_requests(request):
    patient, err = _patient_required(request)
    if err:
        return err
    requests_qs = LabTestRequest.objects.filter(patient=patient).prefetch_related('items').order_by('-created_at')[:20]
    data = [{
        'request_number': r.request_number,
        'status': r.status,
        'status_display': r.get_status_display(),
        'total': str(r.total_amount),
        'created_at': r.created_at.strftime('%d %b %Y'),
        'tests': [i.test_name for i in r.items.all()],
    } for r in requests_qs]
    return JsonResponse({'lab_requests': data})


def patient_api_physio(request):
    patient, err = _patient_required(request)
    if err:
        return err
    physio = patient.created_by
    if not physio:
        # Self-registered patients have no created_by -- fall back to the
        # most recent pairing (e.g. from scanning a physio's pairing QR).
        pairing = PatientPhysioPairing.objects.filter(patient=patient).order_by('-paired_at').first()
        physio = pairing.physio if pairing else None
    if not physio:
        return JsonResponse({'physio': None})
    return JsonResponse({'physio': {
        'name': physio.get_full_name() or physio.username,
        'email': physio.email,
        'username': physio.username,
        # Surfaced so a patient can see their physio actually holds a
        # checked professional credential, not just a self-entered field --
        # see account_app.models.User.license_verified.
        'license_number': physio.license_number if physio.license_number != 'temporary' else None,
        'license_verified': physio.license_verified,
    }})


def patient_api_recommended(request):
    patient, err = _patient_required(request)
    if err:
        return err

    # Physio hand-picked products
    manual_recs = (
        PatientProductRecommendation.objects.filter(patient=patient)
        .select_related('product', 'product__category')
    )
    manual_ids = list(manual_recs.values_list('product_id', flat=True))

    def _product_dict(p, note='', source='auto'):
        return {
            'id': p.id,
            'name': p.name,
            'price': str(p.price),
            'unit': p.unit,
            'category': p.category.name if p.category else '',
            'category_icon': p.category.icon if p.category else '📦',
            'image_url': _image_url(request, p.image),
            'description': p.description,
            'note': note,
            'source': source,   # 'physio_pick' | 'auto'
        }

    physio_picks = [_product_dict(r.product, note=r.note, source='physio_pick') for r in manual_recs]

    # Auto-suggested from diagnosis
    auto_qs, matched_label = get_recommended_for_diagnosis(patient.patient_diagnosis)
    auto_qs = auto_qs.exclude(id__in=manual_ids).select_related('category')[:8]
    auto_picks = [_product_dict(p, source='auto') for p in auto_qs]

    return JsonResponse({
        'physio_picks': physio_picks,
        'auto_suggested': auto_picks,
        'matched_label': matched_label,
        'total': len(physio_picks) + len(auto_picks),
    })