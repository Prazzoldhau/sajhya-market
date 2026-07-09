import json
from decimal import Decimal
from urllib.parse import quote
from django.contrib.auth import authenticate, login, logout
from django.db.models import Max
from django.http import JsonResponse
from django.templatetags.static import static as static_url
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from personal_account.models import AddPatient
from clinic_account.models import Clinic
from exercise_app.models import Region, SubRegion, ExerciseMain, Prescription, PrescriptionExercise
from prescription_app.models import TreatmentSession
from referral_app.models import Referral
from find_physio_app.models import BookingRequest
from marketplace_app.models import Category, Product, Order, OrderItem


# ─── helpers ──────────────────────────────────────────────────────────────────

def _absolute_static_url(request, path):
    """exercise_url / Product.image sometimes store a relative static path
    (e.g. '/static/exercises/lowbackpain/foo.png'), sometimes already a full
    URL, sometimes blank. Normalize to an absolute URL clients can load."""
    if not path:
        return ''
    if path.startswith('http://') or path.startswith('https://'):
        return path
    return request.build_absolute_uri(quote(path, safe='/'))


def _json_body(request):
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return {}


def _require_physio(request):
    """Return user if logged in, else return a 401 JsonResponse."""
    if request.user.is_authenticated:
        return request.user, None
    return None, JsonResponse({'error': 'Authentication required'}, status=401)


# ─── auth ─────────────────────────────────────────────────────────────────────

@ensure_csrf_cookie
def physio_csrf(request):
    return JsonResponse({'detail': 'CSRF cookie set'})


@csrf_exempt
@require_http_methods(["POST"])
def physio_login(request):
    data = _json_body(request)
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return JsonResponse({'error': 'Username and password required'}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'error': 'Invalid credentials'}, status=401)

    login(request, user)
    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'user_type': getattr(user, 'user_type', ''),
            'personal_code': getattr(user, 'personal_code', ''),
        }
    })


@require_http_methods(["POST"])
def physio_logout(request):
    logout(request)
    return JsonResponse({'success': True})


def physio_me(request):
    user, err = _require_physio(request)
    if err:
        return err
    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'user_type': getattr(user, 'user_type', ''),
            'personal_code': getattr(user, 'personal_code', ''),
        }
    })


# ─── patients ─────────────────────────────────────────────────────────────────

def patient_list(request):
    user, err = _require_physio(request)
    if err:
        return err

    if request.method == 'GET':
        q = request.GET.get('q', '').strip()
        qs = AddPatient.objects.filter(created_by=user).order_by('-created_at')
        if q:
            qs = qs.filter(patient_name__icontains=q)
        data = [
            {
                'id': p.id,
                'patient_code': p.patient_code,
                'patient_name': p.patient_name,
                'patient_contact': p.patient_contact,
                'patient_diagnosis': p.patient_diagnosis,
                'completed_session': p.completed_session,
                'created_at': p.created_at.isoformat(),
            }
            for p in qs
        ]
        return JsonResponse({'patients': data})

    if request.method == 'POST':
        data = _json_body(request)
        name = data.get('patient_name', '').strip()
        contact = data.get('patient_contact', '').strip()
        diagnosis = data.get('patient_diagnosis', '').strip()
        clinic_id = data.get('clinic_id')

        if not name or not diagnosis:
            return JsonResponse({'error': 'patient_name and patient_diagnosis are required'}, status=400)

        origin_clinic = None
        if clinic_id:
            try:
                origin_clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                pass

        patient = AddPatient.objects.create(
            patient_name=name,
            patient_contact=contact or '0000000000',
            patient_diagnosis=diagnosis,
            created_by=user,
            origin_clinic=origin_clinic,
        )
        return JsonResponse({
            'success': True,
            'patient': {
                'id': patient.id,
                'patient_code': patient.patient_code,
                'patient_name': patient.patient_name,
            }
        }, status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def patient_detail(request, patient_code):
    user, err = _require_physio(request)
    if err:
        return err

    try:
        patient = AddPatient.objects.get(patient_code=patient_code)
    except AddPatient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)

    prescriptions = Prescription.objects.filter(patient=patient).order_by('-created_at')
    sessions = TreatmentSession.objects.filter(patient=patient).order_by('-session_date')

    return JsonResponse({
        'patient': {
            'id': patient.id,
            'patient_code': patient.patient_code,
            'patient_name': patient.patient_name,
            'patient_contact': patient.patient_contact,
            'patient_diagnosis': patient.patient_diagnosis,
            'completed_session': patient.completed_session,
            'created_at': patient.created_at.isoformat(),
            'qr_token': patient.qr_token or '',
        },
        'prescriptions': [
            {
                'id': p.id,
                'status': p.status,
                'created_at': p.created_at.isoformat(),
                'exercise_count': p.exercises.count(),
            }
            for p in prescriptions
        ],
        'sessions': [
            {
                'id': s.id,
                'session_number': s.session_number,
                'session_note': s.session_note,
                'treatment_response': s.treatment_response,
                'session_date': s.session_date.isoformat(),
            }
            for s in sessions
        ],
    })


# ─── clinics ──────────────────────────────────────────────────────────────────

def clinic_list(request):
    user, err = _require_physio(request)
    if err:
        return err

    if request.method == 'GET':
        clinics = user.clinics.all().order_by('-created_at')
        data = [
            {
                'id': c.id,
                'clinic_code': c.clinic_code,
                'clinic_name': c.clinic_name,
                'address': c.address,
                'phone': c.phone,
                'created_at': c.created_at.isoformat(),
            }
            for c in clinics
        ]
        return JsonResponse({'clinics': data})

    if request.method == 'POST':
        data = _json_body(request)
        name = data.get('clinic_name', '').strip()
        address = data.get('address', '').strip()
        phone = data.get('phone', '').strip()
        pan_number = data.get('pan_number', '').strip() or None

        if not name or not address or not phone:
            return JsonResponse({'error': 'clinic_name, address and phone are required'}, status=400)

        clinic = Clinic.objects.create(
            clinic_name=name,
            address=address,
            phone=phone,
            pan_number=pan_number,
            created_by=user,
        )
        return JsonResponse({
            'success': True,
            'clinic': {
                'id': clinic.id,
                'clinic_code': clinic.clinic_code,
                'clinic_name': clinic.clinic_name,
            },
        }, status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def clinic_detail(request, clinic_id):
    user, err = _require_physio(request)
    if err:
        return err

    try:
        clinic = Clinic.objects.get(id=clinic_id, created_by=user)
    except Clinic.DoesNotExist:
        return JsonResponse({'error': 'Clinic not found'}, status=404)

    patients = AddPatient.objects.filter(origin_clinic=clinic, created_by=user).order_by('-created_at')

    return JsonResponse({
        'clinic': {
            'id': clinic.id,
            'clinic_code': clinic.clinic_code,
            'clinic_name': clinic.clinic_name,
            'address': clinic.address,
            'phone': clinic.phone,
            'created_at': clinic.created_at.isoformat(),
        },
        'patients': [
            {
                'id': p.id,
                'patient_code': p.patient_code,
                'patient_name': p.patient_name,
                'patient_contact': p.patient_contact,
                'patient_diagnosis': p.patient_diagnosis,
                'completed_session': p.completed_session,
                'created_at': p.created_at.isoformat(),
            }
            for p in patients
        ],
    })


# ─── home visits (bookings made to this physio's find-physio profile) ────────

def home_visit_list(request):
    user, err = _require_physio(request)
    if err:
        return err

    bookings = BookingRequest.objects.filter(physio=user, booking_type='home')

    status_filter = request.GET.get('status', '').strip()
    valid_statuses = [s[0] for s in BookingRequest.STATUS]
    if status_filter in valid_statuses:
        bookings = bookings.filter(status=status_filter)

    bookings = bookings.order_by('preferred_date')
    data = [
        {
            'id': b.id,
            'patient_name': b.patient_name,
            'patient_contact': b.patient_contact,
            'patient_email': b.patient_email,
            'condition': b.condition,
            'preferred_date': b.preferred_date.isoformat(),
            'preferred_time': b.preferred_time.isoformat() if b.preferred_time else None,
            'address': b.address,
            'status': b.status,
            'notes': b.notes,
            'total_fee': str(b.total_fee()),
            'created_at': b.created_at.isoformat(),
        }
        for b in bookings
    ]
    return JsonResponse({'home_visits': data})


def home_visit_update_status(request, booking_id):
    user, err = _require_physio(request)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        booking = BookingRequest.objects.get(id=booking_id, physio=user, booking_type='home')
    except BookingRequest.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    data = _json_body(request)
    new_status = data.get('status', '').strip()
    valid_statuses = [s[0] for s in BookingRequest.STATUS]
    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    booking.status = new_status
    notes = data.get('notes', '').strip()
    if notes:
        booking.notes = notes
    booking.save(update_fields=['status', 'notes'])

    return JsonResponse({'success': True, 'status': booking.status})


# ─── shop (marketplace_app) ───────────────────────────────────────────────────

def _product_image_url(request, product):
    """Product.image stores a static-relative path (e.g. 'categorized_product/9/9 (023).png').
    Build a full URL clients can load directly, percent-encoding spaces/parens
    that the raw path may contain."""
    if not product.image:
        return ''
    path = static_url(product.image)
    return request.build_absolute_uri(quote(path, safe='/'))


def shop_category_list(request):
    user, err = _require_physio(request)
    if err:
        return err

    categories = Category.objects.all()
    data = [{'id': c.id, 'name': c.name, 'icon': c.icon} for c in categories]
    return JsonResponse({'categories': data})


def shop_product_list(request):
    user, err = _require_physio(request)
    if err:
        return err

    qs = Product.objects.filter(in_stock=True).select_related('category')

    category_id = request.GET.get('category', '').strip()
    if category_id:
        qs = qs.filter(category_id=category_id)

    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(name__icontains=search)

    qs = qs.order_by('-is_featured', 'name')
    data = [
        {
            'id': p.id,
            'name': p.name,
            'category': p.category.name if p.category else None,
            'category_id': p.category_id,
            'description': p.description,
            'price': str(p.price),
            'unit': p.unit,
            'image': _product_image_url(request, p),
            'is_featured': p.is_featured,
        }
        for p in qs
    ]
    return JsonResponse({'products': data})


def shop_order_list_create(request):
    user, err = _require_physio(request)
    if err:
        return err

    if request.method == 'GET':
        orders = Order.objects.filter(user=user).prefetch_related('items').order_by('-created_at')
        data = [
            {
                'order_number': o.order_number,
                'status': o.status,
                'total_amount': str(o.total_amount),
                'created_at': o.created_at.isoformat(),
                'items': [
                    {'product_name': i.product_name, 'quantity': i.quantity, 'unit_price': str(i.unit_price)}
                    for i in o.items.all()
                ],
            }
            for o in orders
        ]
        return JsonResponse({'orders': data})

    if request.method == 'POST':
        data = _json_body(request)
        items = data.get('items', [])
        customer_name = data.get('customer_name', '').strip() or (user.get_full_name() or user.username)
        customer_email = data.get('customer_email', '').strip() or user.email
        customer_phone = data.get('customer_phone', '').strip()
        delivery_address = data.get('delivery_address', '').strip()
        notes = data.get('notes', '').strip()

        if not items:
            return JsonResponse({'error': 'At least one item is required'}, status=400)
        if not customer_phone or not delivery_address:
            return JsonResponse({'error': 'customer_phone and delivery_address are required'}, status=400)

        order_items = []
        total = Decimal('0.00')
        for item in items:
            try:
                product = Product.objects.get(id=item.get('product_id'), in_stock=True)
            except Product.DoesNotExist:
                continue
            qty = max(1, int(item.get('quantity', 1)))
            order_items.append((product, qty))
            total += product.price * qty

        if not order_items:
            return JsonResponse({'error': 'No valid products in order'}, status=400)

        order = Order.objects.create(
            user=user,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            notes=notes,
            total_amount=total,
        )
        for product, qty in order_items:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                quantity=qty,
                unit_price=product.price,
            )

        return JsonResponse({
            'success': True,
            'order_number': order.order_number,
            'total_amount': str(total),
        }, status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── exercises ────────────────────────────────────────────────────────────────

def region_list(request):
    user, err = _require_physio(request)
    if err:
        return err

    regions = Region.objects.prefetch_related('subregion_set').all()
    data = [
        {
            'id': r.id,
            'region_name': r.region_name,
            'subregions': [
                {'id': sr.id, 'sub_region_name': sr.sub_region_name}
                for sr in r.subregion_set.all()
            ],
        }
        for r in regions
    ]
    return JsonResponse({'regions': data})


def exercise_list(request):
    user, err = _require_physio(request)
    if err:
        return err

    subregion_id = request.GET.get('subregion_id')
    qs = ExerciseMain.objects.select_related('sub_region_fk')
    if subregion_id:
        qs = qs.filter(sub_region_fk_id=subregion_id)

    data = [
        {
            'id': e.id,
            'exercise_name': e.exercise_name,
            'exercise_type': e.exercise_type,
            'difficulty_level': e.difficulty_level,
            'default_sets': e.default_sets,
            'default_reps': e.default_reps,
            'hold_time_sec': e.hold_time_sec,
            'exercise_description': e.exercise_description,
            'exercise_url': _absolute_static_url(request, e.exercise_url),
            'subregion': e.sub_region_fk.sub_region_name,
        }
        for e in qs
    ]
    return JsonResponse({'exercises': data})


# ─── prescriptions ────────────────────────────────────────────────────────────

def prescription_list_create(request, patient_code):
    user, err = _require_physio(request)
    if err:
        return err

    try:
        patient = AddPatient.objects.get(patient_code=patient_code)
    except AddPatient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)

    if request.method == 'GET':
        prescriptions = Prescription.objects.filter(patient=patient).order_by('-created_at')
        data = []
        for p in prescriptions:
            exercises = p.exercises.select_related('exercise').all()
            total = exercises.count()
            completed = exercises.filter(is_completed=True).count()
            data.append({
                'id': p.id,
                'status': p.status,
                'condition_label': p.condition_label,
                'created_at': p.created_at.isoformat(),
                'total_exercises': total,
                'completed_exercises': completed,
                'exercises': [
                    {
                        'id': pe.id,
                        'exercise_id': pe.exercise_id_in_library,
                        'exercise_name': pe.exercise_name,
                        'difficulty_level': pe.difficulty_level,
                        'order': pe.order,
                        'sets': pe.sets,
                        'reps': pe.reps,
                        'hold_time_sec': pe.hold_time_sec,
                        'rest_time_sec': pe.rest_time_sec,
                        'schedule_morning': pe.schedule_morning,
                        'schedule_day': pe.schedule_day,
                        'schedule_evening': pe.schedule_evening,
                        'is_completed': pe.is_completed,
                        'exercise_url': _absolute_static_url(request, pe.exercise.exercise_url if pe.exercise else ''),
                    }
                    for pe in exercises
                ],
            })
        return JsonResponse({'prescriptions': data})

    if request.method == 'POST':
        data = _json_body(request)
        exercise_ids = data.get('exercise_ids', [])  # list of exercise IDs from library
        condition_label = data.get('condition_label', '').strip()

        if not exercise_ids:
            return JsonResponse({'error': 'At least one exercise required'}, status=400)

        prescription = Prescription.objects.create(
            patient=patient,
            created_by=user,
            status='active',
            condition_label=condition_label,
        )

        for order, ex_id in enumerate(exercise_ids):
            try:
                exercise = ExerciseMain.objects.get(id=ex_id)
                PrescriptionExercise.objects.create(
                    prescription=prescription,
                    exercise=exercise,
                    exercise_id_in_library=exercise.id,
                    exercise_name=exercise.exercise_name,
                    difficulty_level=exercise.difficulty_level,
                    order=order,
                )
            except ExerciseMain.DoesNotExist:
                pass

        return JsonResponse({'success': True, 'prescription_id': prescription.id}, status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def prescription_add_exercises(request, prescription_id):
    user, err = _require_physio(request)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        prescription = Prescription.objects.get(id=prescription_id)
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)

    data = _json_body(request)
    exercise_ids = data.get('exercise_ids', [])
    if not exercise_ids:
        return JsonResponse({'error': 'At least one exercise required'}, status=400)

    last_order = prescription.exercises.aggregate(m=Max('order'))['m'] or 0
    added = 0
    for offset, ex_id in enumerate(exercise_ids, start=1):
        try:
            exercise = ExerciseMain.objects.get(id=ex_id)
        except ExerciseMain.DoesNotExist:
            continue
        PrescriptionExercise.objects.create(
            prescription=prescription,
            exercise=exercise,
            exercise_id_in_library=exercise.id,
            exercise_name=exercise.exercise_name,
            difficulty_level=exercise.difficulty_level,
            order=last_order + offset,
        )
        added += 1

    return JsonResponse({'success': True, 'added': added})


def prescription_exercise_toggle(request, exercise_id):
    user, err = _require_physio(request)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        pe = PrescriptionExercise.objects.select_related('prescription').get(id=exercise_id)
    except PrescriptionExercise.DoesNotExist:
        return JsonResponse({'error': 'Exercise not found'}, status=404)

    data = _json_body(request)
    is_completed = bool(data.get('is_completed', not pe.is_completed))
    pe.is_completed = is_completed
    pe.completed_at = timezone.now() if is_completed else None
    pe.save(update_fields=['is_completed', 'completed_at'])

    prescription = pe.prescription
    exercises = prescription.exercises.all()
    total = exercises.count()
    completed = exercises.filter(is_completed=True).count()

    return JsonResponse({
        'success': True,
        'exercise_id': pe.id,
        'is_completed': pe.is_completed,
        'prescription_id': prescription.id,
        'total_exercises': total,
        'completed_exercises': completed,
    })


def prescription_exercise_remove(request, exercise_id):
    user, err = _require_physio(request)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        pe = PrescriptionExercise.objects.select_related('prescription').get(id=exercise_id)
    except PrescriptionExercise.DoesNotExist:
        return JsonResponse({'error': 'Exercise not found'}, status=404)

    prescription = pe.prescription
    pe.delete()

    exercises = prescription.exercises.all()
    total = exercises.count()
    completed = exercises.filter(is_completed=True).count()

    return JsonResponse({
        'success': True,
        'prescription_id': prescription.id,
        'total_exercises': total,
        'completed_exercises': completed,
    })


def patient_stats(request, patient_code):
    user, err = _require_physio(request)
    if err:
        return err

    try:
        patient = AddPatient.objects.get(patient_code=patient_code)
    except AddPatient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)

    prescriptions = Prescription.objects.filter(patient=patient)
    total_prescriptions = prescriptions.count()
    active_prescriptions = prescriptions.filter(status='active').count()
    completed_prescriptions = prescriptions.filter(status='completed').count()

    exercises = PrescriptionExercise.objects.filter(prescription__patient=patient)
    total_exercises = exercises.count()
    completed_exercises = exercises.filter(is_completed=True).count()
    overall_completion = round((completed_exercises / total_exercises) * 100, 1) if total_exercises else 0

    total_sessions = TreatmentSession.objects.filter(patient=patient).count()

    return JsonResponse({
        'total_prescriptions': total_prescriptions,
        'active_prescriptions': active_prescriptions,
        'completed_prescriptions': completed_prescriptions,
        'total_exercises': total_exercises,
        'completed_exercises': completed_exercises,
        'overall_completion_percentage': overall_completion,
        'total_sessions': total_sessions,
    })


# ─── sessions ─────────────────────────────────────────────────────────────────

def session_list_create(request, patient_code):
    user, err = _require_physio(request)
    if err:
        return err

    try:
        patient = AddPatient.objects.get(patient_code=patient_code)
    except AddPatient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)

    if request.method == 'GET':
        sessions = TreatmentSession.objects.filter(patient=patient).order_by('-session_date')
        data = [
            {
                'id': s.id,
                'session_number': s.session_number,
                'pre_notes': s.pre_notes,
                'session_note': s.session_note,
                'treatment_response': s.treatment_response,
                'session_date': s.session_date.isoformat(),
            }
            for s in sessions
        ]
        return JsonResponse({'sessions': data})

    if request.method == 'POST':
        data = _json_body(request)
        session_note = data.get('session_note', '').strip()
        pre_notes = data.get('pre_notes', '').strip()
        treatment_response = data.get('treatment_response', '').strip()

        last = TreatmentSession.objects.filter(patient=patient).order_by('-session_number').first()
        next_number = (last.session_number + 1) if last else 1

        session = TreatmentSession.objects.create(
            patient=patient,
            session_number=next_number,
            pre_notes=pre_notes or None,
            session_note=session_note or None,
            treatment_response=treatment_response or None,
        )

        patient.completed_session = next_number
        patient.save(update_fields=['completed_session'])

        return JsonResponse({'success': True, 'session_id': session.id, 'session_number': next_number}, status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── referrals ────────────────────────────────────────────────────────────────

def referral_list_create(request):
    user, err = _require_physio(request)
    if err:
        return err

    if request.method == 'GET':
        referrals = Referral.objects.filter(referred_by=user).select_related('referred_to', 'patient')
        data = [
            {
                'referral_code': r.referral_code,
                'patient_name': r.patient_name,
                'patient_diagnosis': r.patient_diagnosis,
                'referred_to': r.referred_to.get_full_name() or r.referred_to.username if r.referred_to else None,
                'status': r.status,
                'created_at': r.created_at.isoformat(),
                'patient_code': r.patient.patient_code if r.patient else None,
            }
            for r in referrals
        ]
        return JsonResponse({'referrals': data})

    if request.method == 'POST':
        data = _json_body(request)
        patient_name = data.get('patient_name', '').strip()
        patient_diagnosis = data.get('patient_diagnosis', '').strip()
        reason = data.get('reason', '').strip()
        patient_contact = data.get('patient_contact', '').strip()
        notes = data.get('notes', '').strip()
        referred_to_id = data.get('referred_to_id')

        if not patient_name or not patient_diagnosis or not reason:
            return JsonResponse({'error': 'patient_name, patient_diagnosis, and reason are required'}, status=400)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        referred_to = None
        if referred_to_id:
            try:
                referred_to = User.objects.get(id=referred_to_id)
            except User.DoesNotExist:
                pass

        referral = Referral.objects.create(
            referred_by=user,
            patient_name=patient_name,
            patient_contact=patient_contact,
            patient_diagnosis=patient_diagnosis,
            reason=reason,
            notes=notes,
            referred_to=referred_to,
        )
        return JsonResponse({'success': True, 'referral_code': referral.referral_code}, status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def referral_search(request):
    user, err = _require_physio(request)
    if err:
        return err

    code = request.GET.get('code', '').strip().upper()
    if not code:
        return JsonResponse({'error': 'code parameter required'}, status=400)

    try:
        r = Referral.objects.select_related('referred_by', 'referred_to', 'patient').get(referral_code=code)
    except Referral.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    return JsonResponse({
        'referral_code': r.referral_code,
        'patient_name': r.patient_name,
        'patient_contact': r.patient_contact,
        'patient_diagnosis': r.patient_diagnosis,
        'reason': r.reason,
        'notes': r.notes,
        'status': r.status,
        'referred_by': r.referred_by.get_full_name() or r.referred_by.username if r.referred_by else None,
        'referred_to': r.referred_to.get_full_name() or r.referred_to.username if r.referred_to else None,
        'referred_to_id': r.referred_to.id if r.referred_to else None,
        'is_addressed_to_me': r.referred_to_id == user.id if r.referred_to else True,
        'created_at': r.created_at.isoformat(),
        'patient_code': r.patient.patient_code if r.patient else None,
    })


def referral_accept(request, referral_code):
    user, err = _require_physio(request)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        referral = Referral.objects.get(referral_code=referral_code)
    except Referral.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    if referral.referred_to and referral.referred_to != user:
        return JsonResponse({'error': 'This referral is not addressed to you'}, status=403)

    if referral.status != 'pending':
        return JsonResponse({'error': 'Only pending referrals can be accepted'}, status=400)

    data = _json_body(request)
    patient_name = data.get('patient_name', referral.patient_name).strip()
    patient_contact = data.get('patient_contact', referral.patient_contact).strip()
    patient_diagnosis = data.get('patient_diagnosis', referral.patient_diagnosis).strip()

    patient = AddPatient.objects.create(
        patient_name=patient_name,
        patient_contact=patient_contact or '0000000000',
        patient_diagnosis=patient_diagnosis,
        created_by=user,
        origin_clinic=referral.referred_to_clinic,
    )

    referral.patient = patient
    referral.status = 'accepted'
    if not referral.referred_to:
        referral.referred_to = user
    referral.save()

    return JsonResponse({
        'success': True,
        'patient_code': patient.patient_code,
        'patient_name': patient.patient_name,
    })


def referral_reject(request, referral_code):
    user, err = _require_physio(request)
    if err:
        return err

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        referral = Referral.objects.get(referral_code=referral_code)
    except Referral.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    if referral.referred_to and referral.referred_to != user:
        return JsonResponse({'error': 'This referral is not addressed to you'}, status=403)

    if referral.status != 'pending':
        return JsonResponse({'error': 'Only pending referrals can be rejected'}, status=400)

    referral.status = 'rejected'
    if not referral.referred_to:
        referral.referred_to = user
    referral.save()

    return JsonResponse({'success': True})


def dashboard_stats(request):
    user, err = _require_physio(request)
    if err:
        return err

    total_patients = AddPatient.objects.filter(created_by=user).count()
    total_sessions = TreatmentSession.objects.filter(patient__created_by=user).count()

    # Pending referrals directed to this user OR open (no assigned physio)
    pending_to_me = Referral.objects.filter(referred_to=user, status='pending').count()
    pending_open = Referral.objects.filter(referred_to__isnull=True, status='pending').count()
    pending_referrals = pending_to_me + pending_open

    sent_referrals = Referral.objects.filter(referred_by=user).count()

    recent_patients = AddPatient.objects.filter(created_by=user).order_by('-created_at')[:5]

    return JsonResponse({
        'total_patients': total_patients,
        'total_sessions': total_sessions,
        'pending_referrals': pending_referrals,
        'sent_referrals': sent_referrals,
        'recent_patients': [
            {
                'id': p.id,
                'patient_code': p.patient_code,
                'patient_name': p.patient_name,
                'patient_diagnosis': p.patient_diagnosis,
                'completed_session': p.completed_session,
                'created_at': p.created_at.isoformat(),
            }
            for p in recent_patients
        ],
    })


def user_list(request):
    """Return all users so the app can show a 'refer to' picker."""
    user, err = _require_physio(request)
    if err:
        return err

    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.exclude(id=user.id).values('id', 'username', 'first_name', 'last_name')
    data = [
        {
            'id': u['id'],
            'username': u['username'],
            'full_name': f"{u['first_name']} {u['last_name']}".strip() or u['username'],
        }
        for u in users
    ]
    return JsonResponse({'users': data})
