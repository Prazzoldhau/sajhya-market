from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .patientform import PatientForm
from .models import AddPatient
from datetime import datetime
from django.db.models import Q, Sum
from django.http import JsonResponse
from clinic_account.models import ClinicPhysio, Clinic
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


@login_required
def personal_dashboard(request):
    # Base queryset: only patients created by the logged-in user
    patients = AddPatient.objects.filter(created_by=request.user, origin_clinic__isnull=True).order_by('-created_at')

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
    
    
