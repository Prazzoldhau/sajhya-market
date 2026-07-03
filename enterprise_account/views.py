from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.db.models import Count, Q
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_GET

from .models import Enterprise, Department, EnterpriseStaff
from .forms import EnterpriseForm, DepartmentForm
from .decorators import enterprise_role_required

User = get_user_model()

MODULE_METADATA = {
    'inpatient-referral': {
        'label': 'Inpatient Referral Form',
        'description': 'Refer inpatients between departments.',
        'icon': 'fa-file-medical',
        'url_name': 'enterprise-module-inpatient-referral',
    },
    'usg-reporting': {
        'label': 'USG Reporting',
        'description': 'Ultrasound report entry and history.',
        'icon': 'fa-x-ray',
        'url_name': 'enterprise-module-usg-reporting',
    },
    'queue-management': {
        'label': 'Queue Management',
        'description': 'Manage patient queues per department.',
        'icon': 'fa-list-ol',
        'url_name': 'enterprise-module-queue-management',
    },
    'requisition-form': {
        'label': 'Requisition Form',
        'description': 'Request supplies and equipment.',
        'icon': 'fa-clipboard-list',
        'url_name': 'enterprise-module-requisition-form',
    },
    'maintenance-request': {
        'label': 'Maintenance Request',
        'description': 'Log and track maintenance issues.',
        'icon': 'fa-tools',
        'url_name': 'enterprise-module-maintenance-request',
    },
}


@login_required
def enterprise_onboarding(request):
    membership = EnterpriseStaff.objects.filter(user=request.user, is_active=True).first()
    if membership is not None:
        return redirect('enterprise-dashboard')

    if request.method == 'POST':
        form = EnterpriseForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                enterprise = form.save(commit=False)
                enterprise.created_by = request.user
                enterprise.save()
                EnterpriseStaff.objects.create(
                    enterprise=enterprise,
                    user=request.user,
                    role='admin',
                    department=None,
                )
            messages.success(request, f'Enterprise {enterprise.enterprise_name} created with code {enterprise.enterprise_code}')
            return redirect('enterprise-dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EnterpriseForm()

    return render(request, 'enterprise_account/enterprises/create-enterprise.html', {'enterprise_form': form})


@login_required
@enterprise_role_required()
def enterprise_dashboard(request):
    membership = request.enterprise_membership
    enterprise = membership.enterprise

    context = {
        'enterprise': enterprise,
        'membership': membership,
        'is_admin': membership.role == 'admin',
        'is_hod': membership.role == 'hod',
        'modules': [{'key': key, **meta} for key, meta in MODULE_METADATA.items()],
    }

    if membership.role == 'admin':
        departments = Department.objects.filter(enterprise=enterprise).annotate(
            staff_count=Count('staff_members', filter=Q(staff_members__is_active=True, staff_members__role='staff'))
        )
        context['departments'] = departments
        context['total_departments'] = departments.count()
        context['total_staff'] = EnterpriseStaff.objects.filter(
            enterprise=enterprise, is_active=True
        ).exclude(role='admin').count()
    elif membership.role == 'hod':
        department = membership.department
        context['department'] = department
        context['department_staff'] = EnterpriseStaff.objects.filter(
            department=department, role='staff', is_active=True
        ).select_related('user') if department else EnterpriseStaff.objects.none()
    else:
        context['department'] = membership.department

    return render(request, 'enterprise_account/dashboard/enterprise-dashboard.html', context)


@login_required
@enterprise_role_required(roles=['admin'])
def department_list(request):
    membership = request.enterprise_membership
    departments = Department.objects.filter(enterprise=membership.enterprise).annotate(
        staff_count=Count('staff_members', filter=Q(staff_members__is_active=True, staff_members__role='staff'))
    )
    return render(request, 'enterprise_account/departments/department-list.html', {
        'departments': departments,
        'membership': membership,
    })


@login_required
@enterprise_role_required(roles=['admin'])
def department_create(request):
    membership = request.enterprise_membership
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save(commit=False)
            department.enterprise = membership.enterprise
            department.created_by = request.user
            department.save()
            messages.success(request, f'Department {department.department_name} created with code {department.department_code}')
            return redirect('department-list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DepartmentForm()
    return render(request, 'enterprise_account/departments/create-department.html', {
        'department_form': form,
        'membership': membership,
    })


@login_required
@enterprise_role_required(roles=['admin', 'hod'])
def department_detail(request, department_id):
    membership = request.enterprise_membership
    department = get_object_or_404(Department, id=department_id, enterprise=membership.enterprise)

    if membership.role == 'hod' and membership.department_id != department.id:
        messages.error(request, 'You are not the HOD of this department.')
        return redirect('enterprise-dashboard')

    staff = EnterpriseStaff.objects.filter(department=department, role='staff').select_related('user')
    return render(request, 'enterprise_account/departments/department-detail.html', {
        'department': department,
        'staff': staff,
        'membership': membership,
    })


@login_required
@enterprise_role_required(roles=['admin', 'hod'])
@require_GET
def search_enterprise_users(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)

    users = User.objects.filter(
        models.Q(first_name__icontains=query) |
        models.Q(last_name__icontains=query) |
        models.Q(username__icontains=query)
    )[:10]
    data = [{
        'id': u.id,
        'username': u.username,
        'name': f"{u.first_name} {u.last_name}".strip(),
    } for u in users]
    return JsonResponse(data, safe=False)


@login_required
@enterprise_role_required(roles=['admin', 'hod'])
def staff_list(request):
    membership = request.enterprise_membership
    if membership.role == 'admin':
        staff = EnterpriseStaff.objects.filter(enterprise=membership.enterprise).select_related('user', 'department')
    else:
        staff = EnterpriseStaff.objects.filter(
            department=membership.department, role='staff'
        ).select_related('user', 'department')
    return render(request, 'enterprise_account/staff/staff-list.html', {
        'staff': staff,
        'membership': membership,
    })


@login_required
@enterprise_role_required(roles=['admin', 'hod'])
def staff_assign(request):
    membership = request.enterprise_membership
    enterprise = membership.enterprise

    if membership.role == 'admin':
        departments = Department.objects.filter(enterprise=enterprise)
        assignable_roles = EnterpriseStaff.ROLE_CHOICES
    else:
        departments = Department.objects.filter(id=membership.department_id)
        assignable_roles = [c for c in EnterpriseStaff.ROLE_CHOICES if c[0] == 'staff']

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        department_id = request.POST.get('department_id')
        role = request.POST.get('role')

        target_user = get_object_or_404(User, id=user_id)
        role_keys = [c[0] for c in assignable_roles]
        if role not in role_keys:
            messages.error(request, 'You do not have permission to assign that role.')
            return redirect('staff-assign')

        department = None
        if role in ('hod', 'staff'):
            department = get_object_or_404(Department, id=department_id, enterprise=enterprise)
            if membership.role == 'hod' and department.id != membership.department_id:
                messages.error(request, 'You can only assign staff within your own department.')
                return redirect('staff-assign')

        with transaction.atomic():
            EnterpriseStaff.objects.update_or_create(
                enterprise=enterprise,
                user=target_user,
                defaults={'role': role, 'department': department, 'is_active': True},
            )
            if role == 'hod' and department is not None:
                department.hod = target_user
                department.save(update_fields=['hod'])

        messages.success(request, f'{target_user.username} assigned as {dict(EnterpriseStaff.ROLE_CHOICES).get(role)}')
        return redirect('staff-list')

    return render(request, 'enterprise_account/staff/invite-staff.html', {
        'membership': membership,
        'departments': departments,
        'assignable_roles': assignable_roles,
    })


@login_required
@enterprise_role_required()
def module_stub(request, module_key):
    meta = MODULE_METADATA.get(module_key)
    if meta is None:
        raise Http404
    context = {
        'module_key': module_key,
        'module_label': meta['label'],
        'module_description': meta['description'],
        'membership': request.enterprise_membership,
    }
    return render(request, 'enterprise_account/modules/module-stub.html', context)
