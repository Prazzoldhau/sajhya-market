from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Prefetch, F, Count
from personal_account.models import AddPatient, ActivationCard, PatientPhysioPairing, PatientMedicalProfile, PatientMedication, PatientBloodTest, PatientAid, PatientExercise, PatientAssessmentEntry, PatientDietEntry, PatientConsultation, get_nepal_time
from visit_notes_app.models import VisitNote
from assessment_app.models import SpecialTestReference
from exercise_app.models import Prescription, PrescriptionExercise, ExerciseFeedback, Region, SubRegion, ExerciseMain
from marketplace_app.models import Category, Product, ProductImage, ProductVariant, Order, OrderItem, Commission, CommissionRate, PatientProductRecommendation, PharmacyProduct
from lab_app.models import LabTest, LabTestPanel, LabTestRequest, LabTestRequestItem
from marketplace_app.views import get_recommended_for_diagnosis, _get_cart, _get_pharmacy_cart, get_cart_count, get_pharmacy_cart_count
from marketplace_app.templatetags.marketplace_extras import CATEGORY_ICON_IMAGES
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.db import transaction
import json
import logging
from datetime import timedelta, date
from django.utils.dateparse import parse_date
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
                        'hosted_video_url': ti.exercise.hosted_video_url if ti.exercise else None,
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
        identifier = request.POST.get('username', '').strip()
        pin_input = request.POST.get('password', '').strip()

        # Already-enrolled patients still log in with their patient_code
        # (never asked to pick a username); anyone who signed up after
        # usernames existed logs in with that instead. Try username first
        # since patient_code is a fixed PAT-XXXXXX shape that can't collide
        # with a chosen one.
        patient = AddPatient.objects.filter(username__iexact=identifier).first()
        if not patient:
            patient = AddPatient.objects.filter(patient_code=identifier).first()
        # Same rules as patient_api_login: refuse a soft-deleted account, and
        # a self-registered patient has a real hashed password while a
        # physio-created one still uses phone-as-PIN -- both paths must work
        # here since this form is the only web login for either kind.
        if not patient or patient.is_deleted:
            return render(request, 'patient-login.html', {'error': 'Invalid credentials'})

        if patient.password:
            valid = check_password(pin_input, patient.password)
        else:
            valid = patient.patient_contact == pin_input

        if valid:
            request.session['patient_id'] = patient.id
            return redirect('patient-dashboard')

        return render(request, 'patient-login.html', {'error': 'Invalid credentials'})

    # If GET request, show the login form
    return render(request, 'patient-login.html')


def patient_signup(request):
    """Web equivalent of patient_api_signup -- lets a patient create their
    own account straight from the website instead of only via the native
    app. Unlike the API (kept accepting just name + password so an older
    app build doesn't break), this form requires a username too -- it's
    the login identifier going forward instead of the auto-generated,
    never-shown-to-them patient_code."""
    if request.method == "POST":
        patient_name = request.POST.get('patient_name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not patient_name or not username or not password:
            return render(request, 'patient-signup.html', {'error': 'Name, username and password are required'})
        if len(username) < 3:
            return render(request, 'patient-signup.html', {'error': 'Username must be at least 3 characters'})
        if len(password) < 6:
            return render(request, 'patient-signup.html', {'error': 'Password must be at least 6 characters'})
        if password != confirm_password:
            return render(request, 'patient-signup.html', {'error': 'Passwords do not match'})
        if AddPatient.objects.filter(username__iexact=username).exists():
            return render(request, 'patient-signup.html', {'error': 'That username is already taken'})

        patient = AddPatient.objects.create(
            patient_name=patient_name,
            username=username,
            patient_contact='',
            patient_diagnosis='Not specified',
            password=make_password(password),
        )
        request.session['patient_id'] = patient.id
        return redirect('patient-dashboard')

    return render(request, 'patient-signup.html')
    

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
    # Physio hand-picked products -- excludes Pharmacy same as every other
    # Marketplace listing; nothing stops a physio from picking a Pharmacy
    # product here otherwise, which would leak it out of its own tab.
    manual_recs = (
        PatientProductRecommendation.objects.filter(patient=patient)
        .exclude(product__category__name='Pharmacy')
        .select_related('product', 'product__category')
    )
    manual_ids = list(manual_recs.values_list('product_id', flat=True))
    # Auto-suggested from diagnosis (exclude already-picked)
    auto_recs, matched_label = get_recommended_for_diagnosis(patient.patient_diagnosis)
    auto_recs = auto_recs.exclude(id__in=manual_ids).select_related('category')[:4]

    # Same session carts the public Marketplace/Pharmacy pages use (not
    # patient_app's own _get_patient_cart/_get_patient_pharmacy_cart, which
    # back the separate native-app JSON checkout flow) -- this dashboard
    # links out to the website's own view-cart/checkout, same as
    # add_recs_to_cart below, so it has to read the cart those pages read.
    cart = _get_cart(request)
    pharmacy_cart = _get_pharmacy_cart(request)
    cart_count = get_cart_count(request)
    pharmacy_cart_count = get_pharmacy_cart_count(request)
    cart_total = sum((Decimal(str(item['price'])) * item['quantity'] for item in cart.values()), Decimal('0.00'))
    pharmacy_cart_total = sum((Decimal(str(item['price'])) * item['quantity'] for item in pharmacy_cart.values()), Decimal('0.00'))

    lab_requests = LabTestRequest.objects.filter(patient=patient).prefetch_related('items').order_by('-created_at')[:5]

    # Marketplace + Pharmacy orders this patient placed through the app --
    # same synthetic-email lookup patient_api_orders uses, since Order has
    # no real FK to AddPatient (see patient_api_order's own comment on why).
    orders = Order.objects.filter(
        customer_email=f'{patient.patient_code}@sajhya.local'
    ).prefetch_related('items').order_by('-created_at')[:5]

    medical_profile = getattr(patient, 'medical_profile', None)
    medication_count = patient.medications.count()
    blood_test_count = patient.blood_test_entries.count()

    context = {
        'patient': patient,
        'latest_prescription': latest_prescription,
        'exercises': exercises,
        'manual_recs': manual_recs,
        'auto_recs': auto_recs,
        'matched_label': matched_label,
        'vapid_public_key': settings.VAPID_PUBLIC_KEY,
        'cart_count': cart_count,
        'cart_total': cart_total,
        'pharmacy_cart_count': pharmacy_cart_count,
        'pharmacy_cart_total': pharmacy_cart_total,
        'lab_requests': lab_requests,
        'orders': orders,
        'medical_profile': medical_profile,
        'medication_count': medication_count,
        'blood_test_count': blood_test_count,
    }

    return render(request, 'patient-dashboard-image.html', context)


def _medical_profile_context(patient):
    """Shared by the patient's own medical profile page and the physio-
    facing editor (detail_app) -- same data, same template either way,
    only who's allowed to submit the forms differs."""
    medications_by_time = {'morning': [], 'evening': [], 'night': []}
    for m in patient.medications.select_related('pharmacy_product', 'recorded_by'):
        medications_by_time[m.time_of_day].append(m)

    blood_tests = patient.blood_test_entries.select_related('lab_test', 'recorded_by')

    diet_entries_by_meal = {'breakfast': [], 'lunch': [], 'dinner': [], 'snacks': []}
    for d in patient.diet_entries.select_related('recorded_by'):
        diet_entries_by_meal[d.meal_time].append(d)
    diet_columns = [
        {'key': key, 'label': label, 'entries': diet_entries_by_meal[key]}
        for key, label in PatientDietEntry.MEAL_CHOICES
    ]

    consultations = patient.consultations.select_related('recorded_by')
    today = date.today()
    for con in consultations:
        con.followup_due = bool(con.follow_up_date and con.follow_up_date <= today)

    # Physiotherapy sub-tabs -- Assessment (read-only feed of physio-
    # recorded assessment_app records + the patient/physio-added
    # reference-tool list), Exercises (prescribed summary + a search of
    # the exercise library), Aids (physio-picked/diagnosis-match recs,
    # same query the dashboard's "Recommended for You" runs, plus the
    # patient/physio-added aid entries).
    assessments = patient.regional_assessments.all()[:10]
    visit_notes = patient.visit_notes.filter(case_type__in=['neuro', 'geriatric']).order_by('-created_at')[:10]
    scale_assessments = patient.scale_assessments.all()[:10]

    latest_prescription = Prescription.objects.filter(patient=patient).order_by('-created_at').first()
    prescribed_exercises = latest_prescription.exercises.all().order_by('order') if latest_prescription else []

    manual_recs = (
        PatientProductRecommendation.objects.filter(patient=patient)
        .exclude(product__category__name='Pharmacy')
        .select_related('product', 'product__category')
    )
    manual_ids = list(manual_recs.values_list('product_id', flat=True))
    auto_recs, matched_label = get_recommended_for_diagnosis(patient.patient_diagnosis)
    auto_recs = auto_recs.exclude(id__in=manual_ids).select_related('category')[:8]

    aids = patient.aids.select_related('product', 'recorded_by')
    saved_exercises = patient.saved_exercises.select_related('exercise')
    assessment_entries = patient.assessment_entries.select_related('reference', 'recorded_by')

    # Counts for the tab-card badges at the top of the page -- real data
    # only (no invented "pending refill"/"next session" stand-ins for
    # things this app doesn't actually track).
    medication_count = sum(len(v) for v in medications_by_time.values())
    blood_test_count = blood_tests.count()
    diet_count = sum(len(v) for v in diet_entries_by_meal.values())
    consultation_count = consultations.count()
    followup_due_count = sum(1 for con in consultations if con.followup_due)
    physio_record_count = (
        assessments.count() + visit_notes.count() + aids.count()
        + saved_exercises.count() + assessment_entries.count() + scale_assessments.count()
    )

    return {
        'patient': patient,
        'medications_by_time': medications_by_time,
        'blood_tests': blood_tests,
        'assessments': assessments,
        'visit_notes': visit_notes,
        'scale_assessments': scale_assessments,
        'latest_prescription': latest_prescription,
        'prescribed_exercises': prescribed_exercises,
        'manual_recs': manual_recs,
        'auto_recs': auto_recs,
        'matched_label': matched_label,
        'medication_count': medication_count,
        'blood_test_count': blood_test_count,
        'diet_count': diet_count,
        'physio_record_count': physio_record_count,
        'aids': aids,
        'saved_exercises': saved_exercises,
        'assessment_entries': assessment_entries,
        'diet_columns': diet_columns,
        'consultations': consultations,
        'consultation_count': consultation_count,
        'followup_due_count': followup_due_count,
    }


def _attach_medical_profile_urls(context, patient, is_physio):
    """Computes every add/delete/save URL the template needs once, here,
    instead of the template branching on editing_patient_id at every
    single form action -- the only difference between the patient's own
    page and the physio-facing editor (detail_app.physio_medical_profile_page)
    is which set of URLs (session-based vs patient_id-in-path) gets used."""
    if is_physio:
        pid = {'patient_id': patient.id}
        context['medical_profile_save_url'] = reverse('physio-medical-profile', kwargs=pid)
        context['medication_add_url'] = reverse('physio-medication-add', kwargs=pid)
        context['bloodtest_add_url'] = reverse('physio-bloodtest-add', kwargs=pid)
        context['aid_add_url'] = reverse('physio-aid-add', kwargs=pid)
        context['assessment_entry_add_url'] = reverse('physio-assessment-entry-add', kwargs=pid)
        context['diet_add_url'] = reverse('physio-diet-add', kwargs=pid)
        context['consultation_add_url'] = reverse('physio-consultation-add', kwargs=pid)
        med_delete = lambda mid: reverse('physio-medication-delete', kwargs={**pid, 'medication_id': mid})
        bt_delete = lambda bid: reverse('physio-bloodtest-delete', kwargs={**pid, 'bloodtest_id': bid})
        aid_delete = lambda aid: reverse('physio-aid-delete', kwargs={**pid, 'aid_id': aid})
        entry_delete = lambda eid: reverse('physio-assessment-entry-delete', kwargs={**pid, 'entry_id': eid})
        diet_delete = lambda did: reverse('physio-diet-delete', kwargs={**pid, 'diet_id': did})
        consultation_delete = lambda cid: reverse('physio-consultation-delete', kwargs={**pid, 'consultation_id': cid})
    else:
        context['medical_profile_save_url'] = reverse('patient-medical-profile')
        context['medication_add_url'] = reverse('patient-medication-add')
        context['bloodtest_add_url'] = reverse('patient-bloodtest-add')
        context['aid_add_url'] = reverse('patient-aid-add')
        context['assessment_entry_add_url'] = reverse('patient-assessment-entry-add')
        context['diet_add_url'] = reverse('patient-diet-add')
        context['consultation_add_url'] = reverse('patient-consultation-add')
        med_delete = lambda mid: reverse('patient-medication-delete', kwargs={'medication_id': mid})
        bt_delete = lambda bid: reverse('patient-bloodtest-delete', kwargs={'bloodtest_id': bid})
        aid_delete = lambda aid: reverse('patient-aid-delete', kwargs={'aid_id': aid})
        entry_delete = lambda eid: reverse('patient-assessment-entry-delete', kwargs={'entry_id': eid})
        diet_delete = lambda did: reverse('patient-diet-delete', kwargs={'diet_id': did})
        consultation_delete = lambda cid: reverse('patient-consultation-delete', kwargs={'consultation_id': cid})

    for bucket in context['medications_by_time'].values():
        for m in bucket:
            m.delete_url = med_delete(m.id)
    for bt in context['blood_tests']:
        bt.delete_url = bt_delete(bt.id)
    for aid in context['aids']:
        aid.delete_url = aid_delete(aid.id)
    for entry in context['assessment_entries']:
        entry.delete_url = entry_delete(entry.id)
    for col in context['diet_columns']:
        for d in col['entries']:
            d.delete_url = diet_delete(d.id)
    for con in context['consultations']:
        con.delete_url = consultation_delete(con.id)


@patient_login_required
def patient_medical_profile_page(request):
    """Lets a patient view/edit their own standing medical info across
    six tabs (see PatientMedicalProfile docstring for why medications/
    blood tests/physiotherapy history moved out of plain text fields
    into this). This view only handles the Medical Record (allergies/
    history) + Nursing tab's save -- medication/blood test/aid/
    assessment-tool add/delete are their own small endpoints below.

    A physio can edit all the same data for a given patient at
    detail_app's physio_medical_profile_page -- same template, same
    underlying models, just a different actor (see recorded_by/
    last_updated_by on the models this page edits)."""
    patient_id = request.session.get('patient_id')
    patient = get_object_or_404(AddPatient, id=patient_id)
    profile, _ = PatientMedicalProfile.objects.get_or_create(patient=patient)

    saved = False
    if request.method == "POST":
        # Medical Record and Nursing are separate <form> elements on the
        # page (so each tab only submits its own fields) -- only touch a
        # field if its form actually sent it, or the other form's
        # submission would blank it out.
        for field in ('allergies', 'medical_history', 'nursing_vitals',
                      'nursing_wound_catheter_care', 'nursing_mobility_assistance'):
            if field in request.POST:
                setattr(profile, field, request.POST.get(field, '').strip())
        profile.last_updated_by = None
        profile.save()
        saved = True

    context = _medical_profile_context(patient)
    context.update({'profile': profile, 'saved': saved})
    _attach_medical_profile_urls(context, patient, is_physio=False)
    return render(request, 'patient-medical-profile.html', context)


@patient_login_required
def patient_medication_add(request):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        patient = get_object_or_404(AddPatient, id=patient_id)
        time_of_day = request.POST.get('time_of_day', '').strip()
        pharmacy_product_id = request.POST.get('pharmacy_product_id', '').strip()
        custom_name = request.POST.get('custom_name', '').strip()
        instructions = request.POST.get('instructions', '').strip()

        if time_of_day in dict(PatientMedication.TIME_CHOICES) and (pharmacy_product_id or custom_name):
            pharmacy_product = PharmacyProduct.objects.filter(id=pharmacy_product_id).first() if pharmacy_product_id else None
            PatientMedication.objects.create(
                patient=patient,
                time_of_day=time_of_day,
                pharmacy_product=pharmacy_product,
                custom_name='' if pharmacy_product else custom_name,
                instructions=instructions,
            )
    return redirect(f"{reverse('patient-medical-profile')}?tab=medication")


@patient_login_required
def patient_medication_delete(request, medication_id):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        PatientMedication.objects.filter(id=medication_id, patient_id=patient_id).delete()
    return redirect(f"{reverse('patient-medical-profile')}?tab=medication")


@patient_login_required
def patient_bloodtest_add(request):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        patient = get_object_or_404(AddPatient, id=patient_id)
        lab_test_id = request.POST.get('lab_test_id', '').strip()
        custom_name = request.POST.get('custom_name', '').strip()
        notes = request.POST.get('notes', '').strip()

        if lab_test_id or custom_name:
            lab_test = LabTest.objects.filter(id=lab_test_id).first() if lab_test_id else None
            PatientBloodTest.objects.create(
                patient=patient,
                lab_test=lab_test,
                custom_name='' if lab_test else custom_name,
                notes=notes,
            )
    return redirect(f"{reverse('patient-medical-profile')}?tab=blood_tests")


@patient_login_required
def patient_bloodtest_delete(request, bloodtest_id):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        PatientBloodTest.objects.filter(id=bloodtest_id, patient_id=patient_id).delete()
    return redirect(f"{reverse('patient-medical-profile')}?tab=blood_tests")


@patient_login_required
def patient_aid_add(request):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        patient = get_object_or_404(AddPatient, id=patient_id)
        product_id = request.POST.get('product_id', '').strip()
        custom_name = request.POST.get('custom_name', '').strip()
        notes = request.POST.get('notes', '').strip()

        if product_id or custom_name:
            product = Product.objects.filter(id=product_id).first() if product_id else None
            PatientAid.objects.create(
                patient=patient,
                product=product,
                custom_name='' if product else custom_name,
                notes=notes,
            )
    return redirect(f"{reverse('patient-medical-profile')}?tab=physiotherapy&subtab=aids")


@patient_login_required
def patient_aid_delete(request, aid_id):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        PatientAid.objects.filter(id=aid_id, patient_id=patient_id).delete()
    return redirect(f"{reverse('patient-medical-profile')}?tab=physiotherapy&subtab=aids")


@patient_login_required
def patient_exercise_add_bulk(request):
    """Adds every ticked exercise from a library search to the patient's
    own saved list in one go -- multi-select, unlike Medication/Blood
    Tests/Aids's one-at-a-time add, since picking several exercises at
    once from a search is the whole point here."""
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        patient = get_object_or_404(AddPatient, id=patient_id)
        exercise_ids = request.POST.getlist('exercise_ids')
        existing_ids = set(patient.saved_exercises.values_list('exercise_id', flat=True))
        valid_ids = ExerciseMain.objects.filter(id__in=exercise_ids).values_list('id', flat=True)
        new_rows = [
            PatientExercise(patient=patient, exercise_id=eid)
            for eid in valid_ids if eid not in existing_ids
        ]
        PatientExercise.objects.bulk_create(new_rows)
    return redirect(f"{reverse('patient-medical-profile')}?tab=physiotherapy&subtab=exercises")


@patient_login_required
def patient_exercise_delete(request, saved_exercise_id):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        PatientExercise.objects.filter(id=saved_exercise_id, patient_id=patient_id).delete()
    return redirect(f"{reverse('patient-medical-profile')}?tab=physiotherapy&subtab=exercises")


@patient_login_required
def patient_assessment_entry_add(request):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        patient = get_object_or_404(AddPatient, id=patient_id)
        reference_id = request.POST.get('reference_id', '').strip()
        notes = request.POST.get('notes', '').strip()
        reference = SpecialTestReference.objects.filter(id=reference_id, is_active=True).first()
        if reference:
            PatientAssessmentEntry.objects.get_or_create(patient=patient, reference=reference, defaults={'notes': notes})
    return redirect(f"{reverse('patient-medical-profile')}?tab=physiotherapy&subtab=assessment")


@patient_login_required
def patient_assessment_entry_delete(request, entry_id):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        PatientAssessmentEntry.objects.filter(id=entry_id, patient_id=patient_id).delete()
    return redirect(f"{reverse('patient-medical-profile')}?tab=physiotherapy&subtab=assessment")


@patient_login_required
def patient_diet_add(request):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        patient = get_object_or_404(AddPatient, id=patient_id)
        meal_time = request.POST.get('meal_time', '').strip()
        food_item = request.POST.get('food_item', '').strip()
        notes = request.POST.get('notes', '').strip()
        if meal_time in dict(PatientDietEntry.MEAL_CHOICES) and food_item:
            PatientDietEntry.objects.create(patient=patient, meal_time=meal_time, food_item=food_item, notes=notes)
    return redirect(f"{reverse('patient-medical-profile')}?tab=diet")


@patient_login_required
def patient_diet_delete(request, diet_id):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        PatientDietEntry.objects.filter(id=diet_id, patient_id=patient_id).delete()
    return redirect(f"{reverse('patient-medical-profile')}?tab=diet")


@patient_login_required
def patient_consultation_add(request):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        patient = get_object_or_404(AddPatient, id=patient_id)
        doctor_name = request.POST.get('doctor_name', '').strip()
        visit_date = parse_date(request.POST.get('visit_date', '').strip())
        notes = request.POST.get('notes', '').strip()
        follow_up_date = parse_date(request.POST.get('follow_up_date', '').strip())
        if doctor_name and visit_date:
            PatientConsultation.objects.create(
                patient=patient, doctor_name=doctor_name, visit_date=visit_date,
                notes=notes, follow_up_date=follow_up_date,
            )
    return redirect(f"{reverse('patient-medical-profile')}?tab=consultation")


@patient_login_required
def patient_consultation_delete(request, consultation_id):
    if request.method == "POST":
        patient_id = request.session.get('patient_id')
        PatientConsultation.objects.filter(id=consultation_id, patient_id=patient_id).delete()
    return redirect(f"{reverse('patient-medical-profile')}?tab=consultation")


def add_recs_to_cart(request):
    """Add all recommended products for the logged-in patient into the session cart."""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient-login')
    patient = get_object_or_404(AddPatient, id=patient_id)

    from marketplace_app.views import _get_cart, _save_cart
    cart = _get_cart(request)

    # Excludes Pharmacy -- this adds straight to the cart, so a Pharmacy
    # item here wouldn't just be a display leak, it'd actually bypass the
    # Pharmacy tab and land in the general cart.
    manual_recs = PatientProductRecommendation.objects.filter(patient=patient).exclude(product__category__name='Pharmacy').select_related('product', 'product__category')
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
        identifier = data.get('username', '').strip()
        secret = data.get('password', '').strip()

        if not identifier or not secret:
            return JsonResponse({'success': False, 'error': 'Username and password are required'}, status=400)

        # Already-enrolled patients still log in with their patient_code;
        # anyone with a chosen username (see patient_signup/patient_api_signup)
        # logs in with that instead -- try it first since patient_code's
        # fixed PAT-XXXXXX shape can't collide with a chosen one.
        patient = AddPatient.objects.filter(username__iexact=identifier).first()
        if not patient:
            patient = AddPatient.objects.filter(patient_code=identifier).first()
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
                        'hosted_video_url': ti.exercise.hosted_video_url if ti.exercise else None,
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
                        'hosted_video_url': ti.exercise.hosted_video_url if ti.exercise else None,
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
    patient_api_pair_physio (see AddPatient.created_by docstring).

    `username` is optional and accepted here only so an older app build
    that doesn't send one keeps working unchanged -- it still gets a
    patient_code and can log in with that. A build that does send one lets
    the patient log in with it afterward instead (see patient_api_login),
    same as the website's own signup form, which requires it outright."""
    try:
        data = json.loads(request.body)
        patient_name = data.get('patient_name', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not patient_name or not password:
            return JsonResponse({'success': False, 'error': 'Name and password are required'}, status=400)
        if len(password) < 6:
            return JsonResponse({'success': False, 'error': 'Password must be at least 6 characters'}, status=400)
        if username:
            if len(username) < 3:
                return JsonResponse({'success': False, 'error': 'Username must be at least 3 characters'}, status=400)
            if AddPatient.objects.filter(username__iexact=username).exists():
                return JsonResponse({'success': False, 'error': 'That username is already taken'}, status=400)

        patient = AddPatient.objects.create(
            patient_name=patient_name,
            username=username or None,
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
            'username': patient.username,
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


@require_http_methods(['POST'])
def patient_logout_web(request):
    """Web equivalent of patient_api_logout -- the dashboard (and every
    other patient-facing web page) had no way to end the session at all;
    a patient on a shared/public computer had no way to sign out."""
    request.session.flush()
    return redirect('patient-login')


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


def _product_photo_url(request, obj):
    """obj is a Product, ProductVariant, or PharmacyProduct -- see
    marketplace_app.models.ImageUrlMixin.image_url_path for how the path is
    resolved (a direct admin upload takes priority over the older
    static-path convention `.image` when both are set)."""
    path = obj.image_url_path
    if not path:
        return None
    return request.build_absolute_uri(path)


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
            'image_url': _product_photo_url(request, v) if v.image else _product_photo_url(request, product),
        }
        for v in variants
    ]


def _gallery_prefetch():
    """Shared Prefetch for patient_api_products/patient_api_pharmacy_products --
    one query for all products' gallery images instead of one per product."""
    return Prefetch(
        'gallery_images',
        queryset=ProductImage.objects.order_by('order', 'id'),
        to_attr='gallery_images_list',
    )


def _product_images(request, product):
    """Ordered list of image URLs for the detail-page gallery: the main
    product photo first (always present, even if there are zero extra
    gallery photos), then ProductImage rows in order. Expects
    `gallery_images_list` to be prefetched via _gallery_prefetch(); falls
    back to a fresh query if it wasn't."""
    main = _product_photo_url(request, product)
    urls = [main] if main else []
    extra = getattr(product, 'gallery_images_list', None)
    if extra is None:
        extra = product.gallery_images.order_by('order', 'id')
    urls.extend(_product_photo_url(request, img) for img in extra)
    return urls


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
    qs = Product.objects.filter(in_stock=True).exclude(category__name='Pharmacy').select_related('category').prefetch_related(_variants_prefetch(), _gallery_prefetch())
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
        'image_url': _product_photo_url(request, p),
        'images': _product_images(request, p),
        'description': p.description,
        'variants': _product_variants(request, p),
    } for p in qs]
    return JsonResponse({'products': data})


@csrf_exempt
@require_http_methods(["GET"])
def patient_api_products_public(request):
    """Same idea as patient_api_lab_tests_public/patient_api_pharmacy_products_public:
    browse-only, no login required. Unlike pharmacy's public endpoint, this
    one CAN reuse patient_api_products' own query as-is -- the general
    Product catalog wasn't affected by the migration that moved pharmacy
    items into their own table. Adds brand/is_featured to the response,
    which patient_api_products itself doesn't serialize despite both
    existing on the model."""
    qs = Product.objects.filter(in_stock=True).exclude(category__name='Pharmacy').select_related('category').prefetch_related(_variants_prefetch(), _gallery_prefetch())
    cat_id = request.GET.get('category', '').strip()
    if cat_id:
        qs = qs.filter(category_id=cat_id)
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(name__icontains=search)
    data = [{
        'id': p.id,
        'name': p.name,
        'brand': p.brand,
        'price': str(p.price),
        'unit': p.unit,
        'category': p.category.name if p.category else '',
        'image_url': _product_photo_url(request, p),
        'images': _product_images(request, p),
        'description': p.description,
        'is_featured': p.is_featured,
        'variants': _product_variants(request, p),
    } for p in qs]
    return JsonResponse({'products': data})


def patient_api_pharmacy_products(request):
    patient, err = _patient_required(request)
    if err:
        return err
    qs = Product.objects.filter(in_stock=True, category__name='Pharmacy').select_related('category').prefetch_related(_variants_prefetch(), _gallery_prefetch())
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(name__icontains=search)
    data = [{
        'id': p.id,
        'name': p.name,
        'price': str(p.price),
        'unit': p.unit,
        'category': p.category.name if p.category else '',
        'image_url': _product_photo_url(request, p),
        'images': _product_images(request, p),
        'description': p.description,
        'variants': _product_variants(request, p),
    } for p in qs]
    return JsonResponse({'products': data})


@csrf_exempt
@require_http_methods(["GET"])
def patient_api_pharmacy_products_public(request):
    """Same idea as patient_api_lab_tests_public: browse-only, no login
    required. Deliberately NOT just "patient_api_pharmacy_products minus the
    login check" -- that view queries Product/category__name='Pharmacy',
    which migration 0015_migrate_pharmacy_products_to_own_table moved into
    its own PharmacyProduct table and deleted from Product, so that filter
    now matches nothing. PharmacyProduct also has no ProductImage/
    ProductVariant relations (pharmacy items never used variants/gallery),
    so this returns a single image_url and no images/variants lists,
    unlike patient_api_products/patient_api_pharmacy_products."""
    qs = PharmacyProduct.objects.filter(in_stock=True)
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(name__icontains=search)
    qs = qs.order_by('-is_featured', 'name')
    data = [{
        'id': p.id,
        'name': p.name,
        'category': p.category,
        'description': p.description,
        'price': str(p.price),
        'unit': p.unit,
        'image_url': _product_photo_url(request, p),
        'in_stock': p.in_stock,
        'is_featured': p.is_featured,
        'requires_prescription': p.requires_prescription,
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
            'image_url': _product_photo_url(request, variant) if variant and variant.image else _product_photo_url(request, product),
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
        order_type='marketplace',
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


# ==================== PHARMACY CART/CHECKOUT ====================
# A separate cart + checkout pipeline from the marketplace one above,
# mirroring how the public website already treats pharmacy as its own
# thing (marketplace_app.views' pharmacy_add_to_cart/pharmacy_checkout use
# their own _get_pharmacy_cart session key, distinct from the general
# cart). Needed because patient_api_cart_add/patient_api_order only ever
# handle Product ids -- PharmacyProduct lives in its own table (see
# patient_api_pharmacy_products_public's docstring) and has no variants,
# so it can't just be folded into the existing cart_add/order endpoints
# without them needing to guess which table an id belongs to.
#
# Same as the marketplace checkout, this doesn't block ordering an item
# with requires_prescription=True -- no prescription-upload/verification
# step exists anywhere in this codebase yet, patient app or website.

def _get_patient_pharmacy_cart(request):
    return request.session.get('patient_pharmacy_cart', {})


def _save_patient_pharmacy_cart(request, cart):
    request.session['patient_pharmacy_cart'] = cart
    request.session.modified = True


def patient_api_pharmacy_cart(request):
    patient, err = _patient_required(request)
    if err:
        return err
    cart = _get_patient_pharmacy_cart(request)
    items = []
    total = Decimal('0')
    for key, item in cart.items():
        item_total = Decimal(str(item['price'])) * item['quantity']
        total += item_total
        items.append({
            'product_id': int(key),
            'name': item['name'],
            'price': str(item['price']),
            'quantity': item['quantity'],
            'unit': item.get('unit', ''),
            'image_url': item.get('image_url', ''),
            'requires_prescription': item.get('requires_prescription', False),
            'item_total': str(item_total),
        })
    return JsonResponse({
        'items': items,
        'total': str(total),
        'count': sum(i['quantity'] for i in cart.values()),
    })


@csrf_exempt
@require_http_methods(['POST'])
def patient_api_pharmacy_cart_add(request, product_id):
    patient, err = _patient_required(request)
    if err:
        return err
    product = get_object_or_404(PharmacyProduct, id=product_id, in_stock=True)

    cart = _get_patient_pharmacy_cart(request)
    key = str(product_id)
    if key in cart:
        cart[key]['quantity'] += 1
    else:
        cart[key] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': 1,
            'unit': product.unit,
            'image_url': _product_photo_url(request, product),
            'requires_prescription': product.requires_prescription,
        }
    _save_patient_pharmacy_cart(request, cart)
    return JsonResponse({'success': True, 'cart_count': sum(i['quantity'] for i in cart.values())})


@csrf_exempt
@require_http_methods(['POST'])
def patient_api_pharmacy_cart_update(request):
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
        pid = int(data['product_id'])
        qty = int(data.get('quantity', 0))
    except (json.JSONDecodeError, KeyError, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)
    key = str(pid)
    cart = _get_patient_pharmacy_cart(request)
    if key in cart:
        if qty <= 0:
            del cart[key]
        else:
            cart[key]['quantity'] = qty
    _save_patient_pharmacy_cart(request, cart)
    return JsonResponse({'success': True, 'cart_count': sum(i['quantity'] for i in cart.values())})


@csrf_exempt
@require_http_methods(['POST'])
def patient_api_pharmacy_order(request):
    patient, err = _patient_required(request)
    if err:
        return err
    cart = _get_patient_pharmacy_cart(request)
    if not cart:
        return JsonResponse({'error': 'Cart is empty'}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    delivery_address = data.get('delivery_address', '').strip()
    notes = data.get('notes', '').strip()
    customer_phone = data.get('customer_phone', '').strip() or patient.patient_contact
    if not delivery_address:
        return JsonResponse({'error': 'Delivery address required'}, status=400)
    if not customer_phone:
        return JsonResponse({'error': 'Phone number required'}, status=400)

    total = sum(Decimal(str(item['price'])) * item['quantity'] for item in cart.values())

    order = Order.objects.create(
        order_type='pharmacy',
        customer_name=patient.patient_name,
        customer_email=f'{patient.patient_code}@sajhya.local',
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        notes=notes,
        total_amount=total,
    )
    for key, item in cart.items():
        pid = int(key)
        pharmacy_product = PharmacyProduct.objects.filter(id=pid).first()
        OrderItem.objects.create(
            order=order,
            pharmacy_product=pharmacy_product,
            product_name=item['name'],
            quantity=item['quantity'],
            unit_price=Decimal(str(item['price'])),
        )

    # Auto-create commission for referring physio, same as the general order.
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

    _save_patient_pharmacy_cart(request, {})
    return JsonResponse({'success': True, 'order_number': order.order_number, 'total': str(total)})


# ==================== EXERCISE LIBRARY (Browse) ====================
# Read-only: lets a patient explore the exercise library themselves,
# independent of what a physio has actually prescribed them. Deliberately
# not wired into mark-done/feedback/video-click tracking -- those all key
# off a PrescriptionExercise id, not an ExerciseMain id, and a browsed
# exercise has no PrescriptionExercise row (nothing was prescribed). Keeping
# browse response shapes distinct from the prescribed-exercise ones (no
# schedule_*/is_completed fields) is deliberate, not an oversight -- it
# stops the two id spaces from ever being used interchangeably.

@csrf_exempt
@require_http_methods(["GET"])
def patient_api_browse_regions(request):
    patient, err = _patient_required(request)
    if err:
        return err
    # Roughly half of all sub-regions currently have zero exercises in
    # them (placeholders for content not built out yet) -- counts are
    # included so the app can skip listing those as tappable dead ends.
    regions = Region.objects.prefetch_related(
        Prefetch('subregion_set', queryset=SubRegion.objects.annotate(exercise_count=Count('exercisemain')))
    ).order_by('region_name')
    return JsonResponse({'regions': [
        {
            'id': r.id,
            'region_name': r.region_name,
            'subregions': [
                {'id': sr.id, 'sub_region_name': sr.sub_region_name, 'exercise_count': sr.exercise_count}
                for sr in r.subregion_set.all().order_by('sub_region_name')
            ],
        }
        for r in regions
    ]})


@csrf_exempt
@require_http_methods(["GET"])
def patient_api_browse_exercises(request):
    patient, err = _patient_required(request)
    if err:
        return err

    subregion_id = request.GET.get('subregion_id', '').strip()
    if not subregion_id:
        return JsonResponse({'error': 'subregion_id is required'}, status=400)

    qs = ExerciseMain.objects.filter(sub_region_fk_id=subregion_id).prefetch_related('step_images').order_by('exercise_name')
    return JsonResponse({'exercises': [
        {
            'id': e.id,
            'exercise_name': e.exercise_name,
            'exercise_type': e.exercise_type,
            'difficulty_level': e.get_difficulty_level_display(),
            'exercise_url': request.build_absolute_uri(e.exercise_url) if e.exercise_url else None,
            'youtube_url': e.youtube_url,
            'hosted_video_url': e.hosted_video_url,
            'default_sets': e.default_sets,
            'default_reps': e.default_reps,
            'hold_time_sec': e.hold_time_sec,
            'default_rest_time_sec': e.default_rest_time_sec,
            'description': e.exercise_description,
            'description_nepali': e.exercise_description_nepali,
            'step_images': [
                {
                    'order': si.order,
                    'image_url': request.build_absolute_uri(si.image_url) if si.image_url else None,
                    'label': si.label,
                } for si in e.step_images.all()
            ],
        }
        for e in qs
    ]})


@csrf_exempt
@require_http_methods(["GET"])
def patient_api_browse_regions_public(request):
    """Same region/sub-region catalog as patient_api_browse_regions, minus
    the login gate -- the exercise library is generic reference content,
    not tied to any patient, so there's no reason to require an account
    just to browse it. Only *prescribed* exercises (tied to a specific
    patient's Prescription) still require login."""
    regions = Region.objects.prefetch_related(
        Prefetch('subregion_set', queryset=SubRegion.objects.annotate(exercise_count=Count('exercisemain')))
    ).order_by('region_name')
    return JsonResponse({'regions': [
        {
            'id': r.id,
            'region_name': r.region_name,
            'subregions': [
                {'id': sr.id, 'sub_region_name': sr.sub_region_name, 'exercise_count': sr.exercise_count}
                for sr in r.subregion_set.all().order_by('sub_region_name')
            ],
        }
        for r in regions
    ]})


@csrf_exempt
@require_http_methods(["GET"])
def patient_api_browse_exercises_public(request):
    """Same exercise listing as patient_api_browse_exercises, minus the
    login gate -- see patient_api_browse_regions_public."""
    subregion_id = request.GET.get('subregion_id', '').strip()
    if not subregion_id:
        return JsonResponse({'error': 'subregion_id is required'}, status=400)

    qs = ExerciseMain.objects.filter(sub_region_fk_id=subregion_id).prefetch_related('step_images').order_by('exercise_name')
    return JsonResponse({'exercises': [
        {
            'id': e.id,
            'exercise_name': e.exercise_name,
            'exercise_type': e.exercise_type,
            'difficulty_level': e.get_difficulty_level_display(),
            'exercise_url': request.build_absolute_uri(e.exercise_url) if e.exercise_url else None,
            'youtube_url': e.youtube_url,
            'hosted_video_url': e.hosted_video_url,
            'default_sets': e.default_sets,
            'default_reps': e.default_reps,
            'hold_time_sec': e.hold_time_sec,
            'default_rest_time_sec': e.default_rest_time_sec,
            'description': e.exercise_description,
            'description_nepali': e.exercise_description_nepali,
            'step_images': [
                {
                    'order': si.order,
                    'image_url': request.build_absolute_uri(si.image_url) if si.image_url else None,
                    'label': si.label,
                } for si in e.step_images.all()
            ],
        }
        for e in qs
    ]})


@csrf_exempt
@require_http_methods(["GET"])
def patient_api_browse_exercises_search_public(request):
    """Search the exercise library by name across every region/sub-region
    at once -- patient_api_browse_exercises_public is scoped to a single
    sub_region_id, which can't answer "find me an exercise called X"
    without knowing which of the 5 regions to look in first. No login
    required, same reasoning as the other browse-* public endpoints."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'error': 'q is required'}, status=400)

    qs = (
        ExerciseMain.objects
        .filter(exercise_name__icontains=query)
        .select_related('sub_region_fk', 'sub_region_fk__region_fk')
        .prefetch_related('step_images')
        .order_by('exercise_name')[:50]
    )
    return JsonResponse({'exercises': [
        {
            'id': e.id,
            'exercise_name': e.exercise_name,
            'exercise_type': e.exercise_type,
            'difficulty_level': e.get_difficulty_level_display(),
            'exercise_url': request.build_absolute_uri(e.exercise_url) if e.exercise_url else None,
            'youtube_url': e.youtube_url,
            'hosted_video_url': e.hosted_video_url,
            'default_sets': e.default_sets,
            'default_reps': e.default_reps,
            'hold_time_sec': e.hold_time_sec,
            'default_rest_time_sec': e.default_rest_time_sec,
            'description': e.exercise_description,
            'description_nepali': e.exercise_description_nepali,
            'sub_region_id': e.sub_region_fk_id,
            'sub_region_name': e.sub_region_fk.sub_region_name,
            'region_name': e.sub_region_fk.region_fk.region_name,
            'step_images': [
                {
                    'order': si.order,
                    'image_url': request.build_absolute_uri(si.image_url) if si.image_url else None,
                    'label': si.label,
                } for si in e.step_images.all()
            ],
        }
        for e in qs
    ]})


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
@require_http_methods(["GET"])
def patient_api_lab_tests_public(request):
    """Same catalog as patient_api_lab_tests, minus the login gate -- for
    apps/surfaces that want to show the lab test list (browse only, no
    booking) without requiring a patient account. Booking still goes
    through patient_api_lab_request_create, which does require login."""
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


def patient_api_assessment_tests_public(request):
    """assessment_app's SpecialTestReference catalog (standardized
    assessment tools/special tests, e.g. Berg Balance Scale, TUG, SLR
    Test), browse-only -- same idea as patient_api_lab_tests_public,
    powers the Physiotherapy > Assessment tab's search-and-add."""
    tests = SpecialTestReference.objects.filter(is_active=True)
    return JsonResponse({'assessment_tests': [
        {
            'id': t.id,
            'name': t.name,
            'region': t.region,
            'region_display': t.get_region_display(),
            'purpose': t.purpose,
        }
        for t in tests
    ]})


@csrf_exempt
@require_http_methods(["GET"])
def patient_api_lab_panels_public(request):
    """Bundled packages (Diabetes Panel, Fever Panel, Master Health Checkup,
    etc) -- same no-login browse access as patient_api_lab_tests_public.
    Booking a panel still requires going through
    patient_api_lab_request_create with the panel's individual test ids."""
    panels = LabTestPanel.objects.filter(is_active=True).prefetch_related('tests').order_by('-is_featured', 'name')
    return JsonResponse({'lab_panels': [
        {
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'price': str(p.price),
            'a_la_carte_total': str(p.a_la_carte_total),
            'savings': str(p.savings),
            'is_featured': p.is_featured,
            'test_ids': [t.id for t in p.tests.all()],
            'tests': [t.name for t in p.tests.all()],
        }
        for p in panels
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

    # Physio hand-picked products -- excludes Pharmacy same as every other
    # Marketplace listing; nothing stops a physio from picking a Pharmacy
    # product here otherwise, which would leak it out of its own tab.
    manual_recs = (
        PatientProductRecommendation.objects.filter(patient=patient)
        .exclude(product__category__name='Pharmacy')
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
            'image_url': _product_photo_url(request, p),
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


def _medical_profile_dict(profile):
    patient = profile.patient
    return {
        'allergies': profile.allergies,
        'medical_history': profile.medical_history,
        'nursing_vitals': profile.nursing_vitals,
        'nursing_wound_catheter_care': profile.nursing_wound_catheter_care,
        'nursing_mobility_assistance': profile.nursing_mobility_assistance,
        'updated_at': profile.updated_at.isoformat(),
        'medications': [
            {
                'id': m.id,
                'time_of_day': m.time_of_day,
                'name': m.display_name,
                'instructions': m.instructions,
            } for m in patient.medications.select_related('pharmacy_product')
        ],
        'blood_tests': [
            {
                'id': b.id,
                'name': b.display_name,
                'notes': b.notes,
            } for b in patient.blood_test_entries.select_related('lab_test')
        ],
        'aids': [
            {
                'id': a.id,
                'name': a.display_name,
                'notes': a.notes,
            } for a in patient.aids.select_related('product')
        ],
        'saved_exercises': [
            {
                'id': se.id,
                'exercise_id': se.exercise_id,
                'name': se.exercise.exercise_name,
            } for se in patient.saved_exercises.select_related('exercise')
        ],
        'assessment_entries': [
            {
                'id': ae.id,
                'reference_id': ae.reference_id,
                'name': ae.reference.name,
                'notes': ae.notes,
            } for ae in patient.assessment_entries.select_related('reference')
        ],
        'diet_entries': [
            {
                'id': d.id,
                'meal_time': d.meal_time,
                'food_item': d.food_item,
                'notes': d.notes,
            } for d in patient.diet_entries.all()
        ],
        'consultations': [
            {
                'id': c.id,
                'doctor_name': c.doctor_name,
                'visit_date': c.visit_date.isoformat(),
                'notes': c.notes,
                'follow_up_date': c.follow_up_date.isoformat() if c.follow_up_date else None,
            } for c in patient.consultations.all()
        ],
    }


@csrf_exempt
@require_http_methods(["GET"])
def patient_api_medical_profile(request):
    patient, err = _patient_required(request)
    if err:
        return err
    profile, _ = PatientMedicalProfile.objects.get_or_create(patient=patient)
    return JsonResponse({'medical_profile': _medical_profile_dict(profile)})


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_medical_profile_update(request):
    """Updates the General (allergies/history) + Nursing fields only --
    medications/blood tests go through their own add/delete endpoints
    below, mirroring the website (see patient_medication_add etc.)."""
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    profile, _ = PatientMedicalProfile.objects.get_or_create(patient=patient)
    for field in ('allergies', 'medical_history', 'nursing_vitals', 'nursing_wound_catheter_care', 'nursing_mobility_assistance'):
        if field in data:
            setattr(profile, field, str(data[field]).strip())
    profile.save()
    return JsonResponse({'success': True, 'medical_profile': _medical_profile_dict(profile)})


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_medication_add(request):
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    time_of_day = data.get('time_of_day', '').strip()
    pharmacy_product_id = data.get('pharmacy_product_id')
    custom_name = data.get('custom_name', '').strip()
    instructions = data.get('instructions', '').strip()

    if time_of_day not in dict(PatientMedication.TIME_CHOICES):
        return JsonResponse({'success': False, 'error': 'Invalid time_of_day'}, status=400)
    pharmacy_product = PharmacyProduct.objects.filter(id=pharmacy_product_id).first() if pharmacy_product_id else None
    if not pharmacy_product and not custom_name:
        return JsonResponse({'success': False, 'error': 'pharmacy_product_id or custom_name required'}, status=400)

    medication = PatientMedication.objects.create(
        patient=patient,
        time_of_day=time_of_day,
        pharmacy_product=pharmacy_product,
        custom_name='' if pharmacy_product else custom_name,
        instructions=instructions,
    )
    return JsonResponse({'success': True, 'id': medication.id, 'name': medication.display_name}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_medication_delete(request, medication_id):
    patient, err = _patient_required(request)
    if err:
        return err
    PatientMedication.objects.filter(id=medication_id, patient=patient).delete()
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_bloodtest_add(request):
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    lab_test_id = data.get('lab_test_id')
    custom_name = data.get('custom_name', '').strip()
    notes = data.get('notes', '').strip()

    lab_test = LabTest.objects.filter(id=lab_test_id).first() if lab_test_id else None
    if not lab_test and not custom_name:
        return JsonResponse({'success': False, 'error': 'lab_test_id or custom_name required'}, status=400)

    blood_test = PatientBloodTest.objects.create(
        patient=patient,
        lab_test=lab_test,
        custom_name='' if lab_test else custom_name,
        notes=notes,
    )
    return JsonResponse({'success': True, 'id': blood_test.id, 'name': blood_test.display_name}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_bloodtest_delete(request, bloodtest_id):
    patient, err = _patient_required(request)
    if err:
        return err
    PatientBloodTest.objects.filter(id=bloodtest_id, patient=patient).delete()
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_aid_add(request):
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    product_id = data.get('product_id')
    custom_name = data.get('custom_name', '').strip()
    notes = data.get('notes', '').strip()

    product = Product.objects.filter(id=product_id).first() if product_id else None
    if not product and not custom_name:
        return JsonResponse({'success': False, 'error': 'product_id or custom_name required'}, status=400)

    aid = PatientAid.objects.create(
        patient=patient,
        product=product,
        custom_name='' if product else custom_name,
        notes=notes,
    )
    return JsonResponse({'success': True, 'id': aid.id, 'name': aid.display_name}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_aid_delete(request, aid_id):
    patient, err = _patient_required(request)
    if err:
        return err
    PatientAid.objects.filter(id=aid_id, patient=patient).delete()
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_exercise_add_bulk(request):
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    exercise_ids = data.get('exercise_ids') or []
    existing_ids = set(patient.saved_exercises.values_list('exercise_id', flat=True))
    valid_ids = ExerciseMain.objects.filter(id__in=exercise_ids).values_list('id', flat=True)
    new_rows = [PatientExercise(patient=patient, exercise_id=eid) for eid in valid_ids if eid not in existing_ids]
    PatientExercise.objects.bulk_create(new_rows)
    return JsonResponse({'success': True, 'added': len(new_rows)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_exercise_delete(request, saved_exercise_id):
    patient, err = _patient_required(request)
    if err:
        return err
    PatientExercise.objects.filter(id=saved_exercise_id, patient=patient).delete()
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_assessment_entry_add(request):
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    reference_id = data.get('reference_id')
    notes = data.get('notes', '').strip()
    reference = SpecialTestReference.objects.filter(id=reference_id, is_active=True).first()
    if not reference:
        return JsonResponse({'success': False, 'error': 'reference_id required'}, status=400)

    entry, _ = PatientAssessmentEntry.objects.get_or_create(patient=patient, reference=reference, defaults={'notes': notes})
    return JsonResponse({'success': True, 'id': entry.id, 'name': entry.reference.name}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_assessment_entry_delete(request, entry_id):
    patient, err = _patient_required(request)
    if err:
        return err
    PatientAssessmentEntry.objects.filter(id=entry_id, patient=patient).delete()
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_diet_add(request):
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    meal_time = data.get('meal_time', '').strip()
    food_item = data.get('food_item', '').strip()
    notes = data.get('notes', '').strip()
    if meal_time not in dict(PatientDietEntry.MEAL_CHOICES):
        return JsonResponse({'success': False, 'error': 'Invalid meal_time'}, status=400)
    if not food_item:
        return JsonResponse({'success': False, 'error': 'food_item required'}, status=400)

    entry = PatientDietEntry.objects.create(patient=patient, meal_time=meal_time, food_item=food_item, notes=notes)
    return JsonResponse({'success': True, 'id': entry.id, 'food_item': entry.food_item}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_diet_delete(request, diet_id):
    patient, err = _patient_required(request)
    if err:
        return err
    PatientDietEntry.objects.filter(id=diet_id, patient=patient).delete()
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_consultation_add(request):
    patient, err = _patient_required(request)
    if err:
        return err
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    doctor_name = data.get('doctor_name', '').strip()
    visit_date = parse_date(data.get('visit_date', '').strip())
    notes = data.get('notes', '').strip()
    follow_up_date = parse_date(data.get('follow_up_date', '').strip()) if data.get('follow_up_date') else None
    if not doctor_name:
        return JsonResponse({'success': False, 'error': 'doctor_name required'}, status=400)
    if not visit_date:
        return JsonResponse({'success': False, 'error': 'valid visit_date (YYYY-MM-DD) required'}, status=400)

    entry = PatientConsultation.objects.create(
        patient=patient, doctor_name=doctor_name, visit_date=visit_date,
        notes=notes, follow_up_date=follow_up_date,
    )
    return JsonResponse({'success': True, 'id': entry.id, 'doctor_name': entry.doctor_name}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def patient_api_consultation_delete(request, consultation_id):
    patient, err = _patient_required(request)
    if err:
        return err
    PatientConsultation.objects.filter(id=consultation_id, patient=patient).delete()
    return JsonResponse({'success': True})