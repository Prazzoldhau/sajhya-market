from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .patientform import PatientForm
from .models import AddPatient, PatientPhysioPairing
from datetime import datetime
from django.db.models import Q, Sum
from django.http import JsonResponse
from clinic_account.models import ClinicPhysio, Clinic
from enterprise_account.models import EnterpriseStaff, Enterprise
from account_app.models import User
from marketplace_app.models import Commission



@login_required
def create_patient(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user   # explicit assignment
            patient.save()  # patient_code auto-generated via save() method
            messages.success(request, f'Patient {patient.patient_name} added with code {patient.patient_code}')
            return redirect('personal-dashboard')  # adjust to your URL name
    else:
        form = PatientForm()
    
    return render(request, 'patients/create-patient.html', {'patient_form': form})


def _dashboard_url_name(user):
    return {'clinic': 'clinic-dashboard', 'enterprise': 'enterprise-dashboard'}.get(user.user_type, 'personal-dashboard')


@login_required
def pair_existing_patient(request):
    """Lets a physio link themselves to an already-existing patient --
    most often a self-registered one with no created_by -- by their
    Patient Code or username, instead of only being reachable by the
    patient scanning the physio's QR from the app (patient_api_pair_physio,
    the only way this could happen before). Purely additive: creates a
    PatientPhysioPairing row and never touches AddPatient.created_by, so
    it can't take a patient away from whoever already has access."""
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        patient = AddPatient.objects.filter(patient_code=identifier, is_deleted=False).first()
        if not patient:
            patient = AddPatient.objects.filter(username__iexact=identifier, is_deleted=False).first()

        if not patient:
            messages.error(request, f'No patient found with code or username "{identifier}".')
            return redirect('pair-existing-patient')

        pairing, created = PatientPhysioPairing.objects.get_or_create(
            patient=patient, physio=request.user,
            defaults={'source': 'physio_claimed'},
        )
        if created:
            messages.success(request, f'{patient.patient_name} ({patient.patient_code}) is now linked to your patient list.')
        else:
            messages.info(request, f'{patient.patient_name} was already linked to you.')
        return redirect(_dashboard_url_name(request.user))

    pairings = PatientPhysioPairing.objects.filter(physio=request.user).select_related('patient').order_by('-paired_at')
    return render(request, 'patients/pair-existing-patient.html', {'pairings': pairings})


@login_required
def unpair_patient(request, pairing_id):
    """Undoes pair_existing_patient (or an app-side QR pairing) -- a
    correction path for mistyped codes or a patient who shouldn't have
    been linked. Only ever deletes the PatientPhysioPairing row, never
    the patient record itself, and only this physio's own pairing."""
    if request.method == 'POST':
        pairing = PatientPhysioPairing.objects.filter(id=pairing_id, physio=request.user).first()
        if pairing:
            patient_name = pairing.patient.patient_name
            pairing.delete()
            messages.success(request, f'{patient_name} removed from your patient list.')
    return redirect(_dashboard_url_name(request.user))


@login_required
def personal_dashboard(request):
    # Patients this user either created directly, or has been linked to
    # via PatientPhysioPairing (self-registered patients paired by QR
    # from the app, or added here by code/username) -- created_by alone
    # used to miss every paired-but-not-created patient entirely.
    paired_ids = PatientPhysioPairing.objects.filter(physio=request.user).values_list('patient_id', flat=True)
    patients = AddPatient.objects.filter(
        Q(created_by=request.user) | Q(id__in=paired_ids),
        origin_clinic__isnull=True, origin_enterprise__isnull=True,
    ).distinct().order_by('-created_at')

    # --- Search handling ---
    search_type = request.GET.get('search_type')
    search_value = request.GET.get('search_value')
    if search_type and search_value:
        if search_type == 'name':
            patients = patients.filter(patient_name__icontains=search_value)
        elif search_type == 'code':
            patients = patients.filter(patient_code__icontains=search_value)
        elif search_type == 'contact':
            patients = patients.filter(patient_contact__icontains=search_value)

    # --- Date range filtering ---
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

    # Commission summary
    commissions = Commission.objects.filter(physio=request.user).order_by('-created_at')
    commission_pending = commissions.filter(status='pending').aggregate(t=Sum('commission_amount'))['t'] or 0
    commission_earned  = commissions.filter(status__in=['approved', 'paid']).aggregate(t=Sum('commission_amount'))['t'] or 0

    context = {
        'patients': patients,
        'total_count': total_count,
        'commissions': commissions[:10],
        'commission_pending': commission_pending,
        'commission_earned': commission_earned,
    }
    return render(request, 'dashboard/personal-dashboard.html', context)



@login_required
def get_my_clinics(request):
    try:
        user = request.user
        links = ClinicPhysio.objects.filter(physio=user, is_active=True).select_related('clinic')
        clinic_data = [{
            'clinic_id': link.clinic.id,
            'clinic_code': link.clinic.clinic_code,
            'clinic_name': link.clinic.clinic_name,
            'joined_at': link.joined_at,
            'is_active': link.is_active,
        } for link in links]
        # return JsonResponse({'clinics': clinic_data})
        return render(request, 'working-clinic/assigned-clinic-dashboard.html', {'clinics': clinic_data})
    except Exception as e:
        # Log the error for debugging (check terminal)
        print(f"ERROR in get_my_clinics: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_my_enterprises(request):
    try:
        user = request.user
        links = EnterpriseStaff.objects.filter(physio=user, is_active=True).select_related('enterprise')
        enterprise_data = [{
            'enterprise_id': link.enterprise.id,
            'enterprise_code': link.enterprise.enterprise_code,
            'enterprise_name': link.enterprise.enterprise_name,
            'joined_at': link.joined_at,
            'is_active': link.is_active,
        } for link in links]
        return render(request, 'working-enterprise/assigned-enterprise-dashboard.html', {'enterprises': enterprise_data})
    except Exception as e:
        print(f"ERROR in get_my_enterprises: {e}")
        return JsonResponse({'error': str(e)}, status=500)


    


@login_required   
def assigned_clinic_dashboard(request, clinic_id):
    user = request.user
    
    # 1. Get clinic + verify access
    clinic = get_object_or_404(
        Clinic,
        id=clinic_id,
        registered_clinic__physio=user,
        registered_clinic__is_active=True
    )
    
    # 2. Base queryset: all patients of this clinic
    # Option A: Only patients created by this physio (like personal dashboard)
    patients = AddPatient.objects.filter(origin_clinic=clinic, created_by=user)
    # Option B: All patients of the clinic (regardless of creator)
    # patients = AddPatient.objects.filter(origin_clinic=clinic)
    
    # 3. Apply search filters (same logic as personal_dashboard)
    search_type = request.GET.get('search_type')
    search_value = request.GET.get('search_value')
    if search_type and search_value:
        if search_type == 'name':
            patients = patients.filter(patient_name__icontains=search_value)
        elif search_type == 'code':
            patients = patients.filter(patient_code__icontains=search_value)
        elif search_type == 'contact':
            patients = patients.filter(patient_contact__icontains=search_value)
    
    # 4. Date range filtering
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
    
    # 5. Ordering and count
    patients = patients.order_by('-created_at')
    total_count = patients.count()
    
    context = {
        'clinic': clinic,
        'patients': patients,
        'total_count': total_count,
    }
    return render(request, 'working-clinic/personal-clinic-detail.html', context)


@login_required
def add_patient_to_clinic(request, clinic_id):
    clinic = get_object_or_404(Clinic, id=clinic_id)

    # Optional: verify physio has access to this clinic (same security as before)
    if not ClinicPhysio.objects.filter(physio=request.user, clinic=clinic, is_active=True).exists():
        messages.error(request, "You don't have access to this clinic.")
        return redirect('assigned-clinic-dashboard', clinic_id=clinic_id)

    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():   # ← note the parentheses
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.origin_clinic = clinic
            patient.save()
            messages.success(request, f"Patient {patient.patient_name} added with code {patient.patient_code}")
            return redirect('assigned-clinic-dashboard', clinic_id=clinic_id)  # or stay on same page
        else:
            # Form is invalid – show errors
            messages.error(request, "Please correct the errors below.")
    else:
        form = PatientForm()

    return render(request, 'patients/create-patient.html', {
        'patient_form': form,
        'clinic': clinic,          # pass clinic to template
        'clinic_id': clinic.id,
    })


@login_required
def assigned_enterprise_dashboard(request, enterprise_id):
    user = request.user

    enterprise = get_object_or_404(
        Enterprise,
        id=enterprise_id,
        registered_enterprise__physio=user,
        registered_enterprise__is_active=True
    )

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
    }
    return render(request, 'working-enterprise/personal-enterprise-detail.html', context)


@login_required
def add_patient_to_enterprise(request, enterprise_id):
    enterprise = get_object_or_404(Enterprise, id=enterprise_id)

    if not EnterpriseStaff.objects.filter(physio=request.user, enterprise=enterprise, is_active=True).exists():
        messages.error(request, "You don't have access to this enterprise.")
        return redirect('assigned-enterprise-dashboard', enterprise_id=enterprise_id)

    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.origin_enterprise = enterprise
            patient.save()
            messages.success(request, f"Patient {patient.patient_name} added with code {patient.patient_code}")
            return redirect('assigned-enterprise-dashboard', enterprise_id=enterprise_id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PatientForm()

    return render(request, 'patients/create-patient.html', {
        'patient_form': form,
        'enterprise': enterprise,
        'enterprise_id': enterprise.id,
    })

    
