from django.shortcuts import render, redirect, get_object_or_404
from personal_account.models import AddPatient
from exercise_app.models import Prescription, PrescriptionExercise, ExerciseFeedback
from marketplace_app.models import Category, Product, Order, OrderItem, Commission, CommissionRate
from django.http import JsonResponse
from django.conf import settings
import json
from decimal import Decimal
from urllib.parse import quote
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

def patient_api_me(request):
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        patient = AddPatient.objects.get(id=patient_id)
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
                        'sets': ti.sets,
                        'reps': ti.reps,
                        'hold_time_sec': ti.hold_time_sec,
                        'rest_time_sec': ti.rest_time_sec,
                    } for ti in through_instances
                ]
            }
        return JsonResponse({
            'success': True,
            'patient_id': patient.id,
            'patient_name': getattr(patient, 'patient_name', 'Patient'),
            'patient_code': patient.patient_code,
            'diagnosis': getattr(patient, 'diagnosis', 'Not specified'),
            'latest_prescription': prescription_data,
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
            return redirect('patient_login')
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
    context = {
        'patient': patient,
        'latest_prescription': latest_prescription,
        'exercises': exercises, 
    }
    
    return render(request, 'patient-dashboard-image.html', context)




# ==================== MOBILE API LOGIN ====================

@csrf_exempt
@require_http_methods(["POST"])
def patient_api_login(request):
    try:
        data = json.loads(request.body)
        patient_code = data.get('username', '').strip()
        pin_input = data.get('password', '').strip()

        if not patient_code or not pin_input:
            return JsonResponse({'success': False, 'error': 'Username and password are required'}, status=400)

        patient = AddPatient.objects.get(patient_code=patient_code)
        if patient.patient_contact != pin_input:
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
                        'sets': ti.sets,
                        'reps': ti.reps,
                        'hold_time_sec': ti.hold_time_sec,
                        'rest_time_sec': ti.rest_time_sec,
                    } for ti in through_instances
                ]
            }

        # Build response
        patient_name = getattr(patient, 'patient_name', 'Patient')
        diagnosis = getattr(patient, 'diagnosis', 'Not specified')
        response_data = {
            'success': True,
            'patient_id': patient.id,
            'patient_name': patient_name,
            'patient_code': patient.patient_code,
            'diagnosis': diagnosis,
            'latest_prescription': prescription_data,
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


# ==================== LOGOUT ====================

@csrf_exempt
@require_http_methods(['POST'])
def patient_api_logout(request):
    request.session.flush()
    return JsonResponse({'success': True})


# ==================== MARKETPLACE API ====================

def _patient_required(request):
    pid = request.session.get('patient_id')
    if not pid:
        return None, JsonResponse({'error': 'Not authenticated'}, status=401)
    try:
        return AddPatient.objects.get(id=pid), None
    except AddPatient.DoesNotExist:
        return None, JsonResponse({'error': 'Patient not found'}, status=404)


def _image_url(request, image_path):
    if not image_path:
        return None
    encoded = quote(image_path, safe='/')
    return request.build_absolute_uri(f'{settings.STATIC_URL}{encoded}')


def _get_patient_cart(request):
    return request.session.get('patient_cart', {})


def _save_patient_cart(request, cart):
    request.session['patient_cart'] = cart
    request.session.modified = True


def patient_api_categories(request):
    patient, err = _patient_required(request)
    if err:
        return err
    cats = Category.objects.all().order_by('id')
    return JsonResponse({'categories': [{'id': c.id, 'name': c.name, 'icon': c.icon} for c in cats]})


def patient_api_products(request):
    patient, err = _patient_required(request)
    if err:
        return err
    qs = Product.objects.filter(in_stock=True).select_related('category')
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
    } for p in qs]
    return JsonResponse({'products': data})


def patient_api_cart(request):
    patient, err = _patient_required(request)
    if err:
        return err
    cart = _get_patient_cart(request)
    items = []
    total = Decimal('0')
    for pid, item in cart.items():
        item_total = Decimal(str(item['price'])) * item['quantity']
        total += item_total
        items.append({
            'product_id': int(pid),
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
    cart = _get_patient_cart(request)
    pid = str(product_id)
    if pid in cart:
        cart[pid]['quantity'] += 1
    else:
        cart[pid] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': 1,
            'unit': product.unit,
            'image_url': _image_url(request, product.image),
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
        pid = str(data['product_id'])
        qty = int(data.get('quantity', 0))
    except (json.JSONDecodeError, KeyError, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)
    cart = _get_patient_cart(request)
    if pid in cart:
        if qty <= 0:
            del cart[pid]
        else:
            cart[pid]['quantity'] = qty
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
    if not delivery_address:
        return JsonResponse({'error': 'Delivery address required'}, status=400)

    total = sum(Decimal(str(item['price'])) * item['quantity'] for item in cart.values())

    order = Order.objects.create(
        customer_name=patient.patient_name,
        customer_email=f'{patient.patient_code}@sajhya.local',
        customer_phone=patient.patient_contact,
        delivery_address=delivery_address,
        notes=notes,
        total_amount=total,
    )
    for pid, item in cart.items():
        try:
            product = Product.objects.get(id=int(pid))
        except Product.DoesNotExist:
            product = None
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=item['name'],
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


def patient_api_physio(request):
    patient, err = _patient_required(request)
    if err:
        return err
    physio = patient.created_by
    if not physio:
        return JsonResponse({'physio': None})
    return JsonResponse({'physio': {
        'name': physio.get_full_name() or physio.username,
        'email': physio.email,
        'username': physio.username,
    }})