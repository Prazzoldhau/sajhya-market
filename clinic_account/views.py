from django.shortcuts import render, redirect
from personal_account import patientform
from django.contrib import messages
from personal_account.models import AddPatient
from datetime import datetime
from .clinicform import ClinicForm
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from account_app.models import User
from django.db import models
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from .models import Clinic, ClinicPhysio
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from marketplace_app.models import Commission



def clinic_user_create_patient(request):
    if request.method == 'POST':
        form = patientform.PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user   # explicit assignment
            patient.save()  # patient_code auto-generated via save() method
            messages.success(request, f'Patient {patient.patient_name} added with code {patient.patient_code}')
            return redirect('clinic-dashboard')  # adjust to your URL name
    else:
        form = patientform.PatientForm()
    
    return render(request, 'patients/create-patient.html', {'patient_form': form})

@login_required
def add_patient_by_clinicuser(request, clinic_id):
    clinic = get_object_or_404(Clinic, id=clinic_id)

    if request.method == 'POST':
        form = patientform.PatientForm(request.POST)
        if form.is_valid():   # ← note the parentheses
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.origin_clinic = clinic
            patient.save()
            messages.success(request, f"Patient {patient.patient_name} added with code {patient.patient_code}")
            return redirect('clinic-detail', clinic_id=clinic_id)  # or stay on same page
        else:
            # Form is invalid – show errors
            messages.error(request, "Please correct the errors below.")
    else:
        form = patientform.PatientForm()

    return render(request, 'patients/create-patient.html', {
        'patient_form': form,
        'clinic': clinic,          # pass clinic to template
        'clinic_id': clinic.id,
    })
    
    

@login_required 
def clinic_dashboard(request):
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
    return render(request, 'dashboard/clinic-dashboard.html', context)




@login_required   
def clinic_detail(request,clinic_id):
    user = request.user
    
    # 1. Get clinic + verify access
    clinic = get_object_or_404(Clinic,id=clinic_id)
    
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
    return render(request, 'details/clinic-detail.html', context)








def clinic_create(request):
    if request.method == 'POST':
        form = ClinicForm(request.POST)
        # views.py
        if form.is_valid():
            clinic = form.save(commit=False)
            clinic.created_by = request.user
            clinic.save()
            
            messages.success(request, f'clinic {clinic.clinic_name} added with code {clinic.clinic_code}')
            return redirect('clinic-sub-dash')  # adjust to your URL name
    else:
        form = ClinicForm()
    
    return render (request, 'clinics/create-clinic.html', {'clinic_form': form})
        
        


@require_GET
def search_physio_list(request):
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    # Search across first_name, last_name, username (case-insensitive)
    physios = User.objects.filter(
        models.Q(license_number__isnull=False) & ~models.Q(license_number__exact='')
    ).filter(
        models.Q(first_name__icontains=query) |
        models.Q(last_name__icontains=query) |
        models.Q(username__icontains=query) |
        models.Q(license_number__icontains=query)
    )[:10]
    data = [{
        'id': p.id,
        'user_name':p.username,
        'name': f"{p.first_name} {p.last_name}".strip(), 
        'registration_number': p.license_number,
        'personal_code': p.personal_code,
    } for p in physios]
    return JsonResponse(data, safe=False)





@login_required
def clinic_list(request):
    # Get clinics owned by the logged‑in user
    clinics = request.user.clinics.all()  # because related_name='clinics'
    return render(request, 'subdashboards/clinicsubdashboard.html', {'clinics': clinics})



@login_required
def search_physio(request, pk):
    clinic = get_object_or_404(Clinic, id=pk, created_by=request.user)
    return render(request, 'staffs/search-physios.html', {'clinic': clinic})


def staff_list(request):
    return render(request, 'staffs/staff-dashboard.html')


    

  


@login_required
def claim_physio(request):
    if request.method == 'POST':
        clinic_id = request.POST.get('clinic_id')
        physio_id = request.POST.get('physio_id')
        
        # Validate clinic exists and user has permission to manage it
        clinic = Clinic.objects.get(id=clinic_id)
        
        if request.user != clinic.created_by:
            return JsonResponse({'error': 'You are not the admin of this clinic'}, status=403)
        
        # Create the relationship
        try:
            clinic_physio, created = ClinicPhysio.objects.get_or_create(
                clinic=clinic,
                physio_id=physio_id,
                defaults={'is_active': True}
            )
            if not created:
                return JsonResponse({'error': 'Physio already claimed for this clinic'}, status=400)
            return JsonResponse({'success': True, 'message': 'Physio claimed successfully'})
        except IntegrityError:
            return JsonResponse({'error': 'Database error, possibly duplicate'}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=405)
