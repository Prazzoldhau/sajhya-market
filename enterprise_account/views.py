from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.templatetags.static import static
from personal_account import patientform
from django.contrib import messages
from personal_account.models import AddPatient
from datetime import datetime
from .enterpriseform import EnterpriseForm, WardForm, PhysioRequestForm, PhysioRequestFormSet, PhysioRequestStatusForm
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum
from .models import Enterprise, EnterpriseStaff, Ward, PhysioRequest
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from marketplace_app.models import Commission
from .decorators import ward_required


def _accessible_enterprise_ids(user):
    """Enterprises this user can see physio requests for: ones they own,
    plus ones they're claimed as staff on (EnterpriseStaff has no separate
    row for the owner -- claim_staff is for adding *other* physios)."""
    staffed_ids = EnterpriseStaff.objects.filter(
        physio=user, is_active=True
    ).values_list('enterprise_id', flat=True)
    return Enterprise.objects.filter(
        Q(created_by=user) | Q(id__in=staffed_ids)
    ).values_list('id', flat=True)


def enterprise_user_create_patient(request):
    if request.method == 'POST':
        form = patientform.PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.save()
            messages.success(request, f'Patient {patient.patient_name} added with code {patient.patient_code}')
            return redirect('enterprise-dashboard')
    else:
        form = patientform.PatientForm()

    return render(request, 'patients/create-patient.html', {'patient_form': form})


@login_required
def add_patient_by_enterpriseuser(request, enterprise_id):
    enterprise = get_object_or_404(Enterprise, id=enterprise_id)

    if request.method == 'POST':
        form = patientform.PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.origin_enterprise = enterprise
            patient.save()
            messages.success(request, f"Patient {patient.patient_name} added with code {patient.patient_code}")
            return redirect('enterprise-detail', enterprise_id=enterprise_id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = patientform.PatientForm()

    return render(request, 'patients/create-patient.html', {
        'patient_form': form,
        'enterprise': enterprise,
        'enterprise_id': enterprise.id,
    })


@login_required
def enterprise_dashboard(request):
    patients = AddPatient.objects.filter(
        created_by=request.user, origin_clinic__isnull=True, origin_enterprise__isnull=True
    ).order_by('-created_at')

    search_type = request.GET.get('search_type')
    search_value = request.GET.get('search_value')
    if search_type and search_value:
        if search_type == 'name':
            patients = patients.filter(patient_name__icontains=search_value)
        elif search_type == 'code':
            patients = patients.filter(patient_code__icontains=search_value)
        elif search_type == 'contact':
            patients = patients.filter(patient_contact__icontains=search_value)

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            patients = patients.filter(created_at__date__gte=from_date_obj)
        except ValueError:
            pass
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            patients = patients.filter(created_at__date__lte=to_date_obj)
        except ValueError:
            pass

    total_count = patients.count()

    commissions = Commission.objects.filter(physio=request.user).order_by('-created_at')
    commission_pending = commissions.filter(status='pending').aggregate(t=Sum('commission_amount'))['t'] or 0
    commission_earned = commissions.filter(status__in=['approved', 'paid']).aggregate(t=Sum('commission_amount'))['t'] or 0

    context = {
        'patients': patients,
        'total_count': total_count,
        'commissions': commissions[:10],
        'commission_pending': commission_pending,
        'commission_earned': commission_earned,
    }
    return render(request, 'dashboard/enterprise-dashboard.html', context)


@login_required
def enterprise_detail(request, enterprise_id):
    user = request.user

    enterprise = get_object_or_404(Enterprise, id=enterprise_id)

    patients = AddPatient.objects.filter(origin_enterprise=enterprise, created_by=user)

    search_type = request.GET.get('search_type')
    search_value = request.GET.get('search_value')
    if search_type and search_value:
        if search_type == 'name':
            patients = patients.filter(patient_name__icontains=search_value)
        elif search_type == 'code':
            patients = patients.filter(patient_code__icontains=search_value)
        elif search_type == 'contact':
            patients = patients.filter(patient_contact__icontains=search_value)

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            patients = patients.filter(created_at__date__gte=from_date_obj)
        except ValueError:
            pass
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            patients = patients.filter(created_at__date__lte=to_date_obj)
        except ValueError:
            pass

    patients = patients.order_by('-created_at')
    total_count = patients.count()

    context = {
        'enterprise': enterprise,
        'patients': patients,
        'total_count': total_count,
        'wards': enterprise.wards.all(),
    }
    return render(request, 'details/enterprise-detail.html', context)


@login_required
def add_ward(request, enterprise_id):
    enterprise = get_object_or_404(Enterprise, id=enterprise_id, created_by=request.user)

    if request.method == 'POST':
        form = WardForm(request.POST)
        if form.is_valid() and Ward.objects.filter(
            enterprise=enterprise, ward_type=form.cleaned_data['ward_type']
        ).exists():
            form.add_error('ward_type', 'This enterprise already has a ward of that type.')

        if form.is_valid():
            ward = form.save(commit=False)
            ward.enterprise = enterprise
            ward.created_by = request.user
            ward.save()
            messages.success(request, f'{ward.get_ward_type_display()} ward added.')
            return redirect('enterprise-detail', enterprise_id=enterprise_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = WardForm()

    return render(request, 'wards/create-ward.html', {'ward_form': form, 'enterprise': enterprise})


def enterprise_create(request):
    if request.method == 'POST':
        form = EnterpriseForm(request.POST)
        if form.is_valid():
            enterprise = form.save(commit=False)
            enterprise.created_by = request.user
            enterprise.save()

            messages.success(request, f'Enterprise {enterprise.enterprise_name} added with code {enterprise.enterprise_code}')
            return redirect('enterprise-sub-dash')
    else:
        form = EnterpriseForm()

    return render(request, 'enterprises/create-enterprise.html', {'enterprise_form': form})


@login_required
def enterprise_list(request):
    enterprises = request.user.enterprises.all()  # related_name='enterprises'
    return render(request, 'subdashboards/enterprisesubdashboard.html', {'enterprises': enterprises})


@login_required
def search_staff(request, pk):
    enterprise = get_object_or_404(Enterprise, id=pk, created_by=request.user)
    return render(request, 'staffs/search-staffs.html', {'enterprise': enterprise})


def staff_list(request):
    return render(request, 'staffs/staff-dashboard.html')


@login_required
def claim_staff(request):
    if request.method == 'POST':
        enterprise_id = request.POST.get('enterprise_id')
        physio_id = request.POST.get('physio_id')

        enterprise = Enterprise.objects.get(id=enterprise_id)

        if request.user != enterprise.created_by:
            return JsonResponse({'error': 'You are not the admin of this enterprise'}, status=403)

        try:
            enterprise_staff, created = EnterpriseStaff.objects.get_or_create(
                enterprise=enterprise,
                physio_id=physio_id,
                defaults={'is_active': True}
            )
            if not created:
                return JsonResponse({'error': 'Physio already claimed for this enterprise'}, status=400)
            return JsonResponse({'success': True, 'message': 'Physio claimed successfully'})
        except IntegrityError:
            return JsonResponse({'error': 'Database error, possibly duplicate'}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=405)


def ward_manifest(request, token):
    """Per-ward PWA manifest -- start_url is ward-specific, so an "Add to
    Home Screen" icon on that ward's shared computer opens straight to this
    ward's request form (not a generic app), without locking the browser
    down to only this page like kiosk mode would."""
    ward = get_object_or_404(Ward, access_token=token)
    manifest = {
        'name': f'Sajhya Physio Request - {ward.get_ward_type_display()}',
        'short_name': 'Physio Request',
        'start_url': request.build_absolute_uri(
            reverse('ward-request-form', kwargs={'token': token})
        ),
        'display': 'standalone',
        'background_color': '#ffffff',
        'theme_color': '#667eea',
        'icons': [
            {'src': static('icons/ward-icon-192.png'), 'sizes': '192x192', 'type': 'image/png'},
            {'src': static('icons/ward-icon-512.png'), 'sizes': '512x512', 'type': 'image/png'},
        ],
    }
    return JsonResponse(manifest, content_type='application/manifest+json')


def ward_service_worker(request, token):
    """Served under this ward's own URL path so its default scope covers
    exactly this ward's pages -- no offline caching, it only exists to
    satisfy the browser's PWA installability requirement."""
    script = (
        "self.addEventListener('install', () => self.skipWaiting());"
        "self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));"
        "self.addEventListener('fetch', () => {});"
    )
    return HttpResponse(script, content_type='application/javascript')


def ward_login(request, token):
    ward = get_object_or_404(Ward, access_token=token)

    bound_ward_id = request.session.get('ward_id')
    if bound_ward_id and bound_ward_id == ward.id:
        return redirect('ward-request-form', token=token)

    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()
        if ward.check_pin(pin):
            request.session['ward_id'] = ward.id
            return redirect('ward-request-form', token=token)
        messages.error(request, 'Incorrect PIN. Please try again.')

    return render(request, 'wards/ward-login.html', {'ward': ward})


@ward_required
def ward_logout(request, token):
    request.session.pop('ward_id', None)
    return redirect('ward-login', token=token)


@ward_required
def ward_request_form(request, token):
    ward = request.ward

    if request.method == 'POST':
        formset = PhysioRequestFormSet(request.POST, queryset=PhysioRequest.objects.none())
        if formset.is_valid():
            created = 0
            for row_form in formset:
                if not row_form.cleaned_data or not row_form.cleaned_data.get('patient_name'):
                    continue
                physio_request = row_form.save(commit=False)
                physio_request.ward = ward
                physio_request.save()
                created += 1
            if created:
                messages.success(request, f'Sent {created} physio request{"s" if created != 1 else ""}.')
            else:
                messages.error(request, 'No patient rows were filled in.')
            return redirect('ward-request-form', token=token)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        formset = PhysioRequestFormSet(queryset=PhysioRequest.objects.none())

    recent_requests = ward.physio_requests.all()[:15]
    return render(request, 'wards/ward-request-form.html', {
        'ward': ward,
        'formset': formset,
        'recent_requests': recent_requests,
    })


@login_required
def physio_requests_queue(request):
    enterprise_ids = _accessible_enterprise_ids(request.user)

    requests_qs = PhysioRequest.objects.filter(
        ward__enterprise_id__in=enterprise_ids
    ).select_related('ward', 'ward__enterprise')

    status = request.GET.get('status', 'pending')
    valid_statuses = [choice[0] for choice in PhysioRequest.STATUS_CHOICES]
    if status in valid_statuses:
        requests_qs = requests_qs.filter(status=status)

    return render(request, 'wards/physio-requests-queue.html', {
        'physio_requests': requests_qs,
        'status': status,
        'status_choices': PhysioRequest.STATUS_CHOICES,
    })


@login_required
def update_request_status(request, request_id):
    enterprise_ids = _accessible_enterprise_ids(request.user)

    physio_request = get_object_or_404(
        PhysioRequest, id=request_id, ward__enterprise_id__in=enterprise_ids
    )

    if request.method == 'POST':
        form = PhysioRequestStatusForm(request.POST, instance=physio_request)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.status_updated_by = request.user
            updated.status_updated_at = timezone.now()
            updated.save()
            messages.success(request, f'Updated {updated.patient_name} to {updated.get_status_display()}.')
        else:
            messages.error(request, 'Please correct the errors below.')

    return redirect('physio-requests-queue')
