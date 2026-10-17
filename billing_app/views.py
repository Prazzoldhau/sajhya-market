from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from personal_account.models import AddPatient

from .forms import BillingEntryForm, PatientPackageForm
from .models import BillingEntry, PatientPackage


@login_required
def billing_list(request):
    if request.method == 'POST':
        form = BillingEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.physio = request.user
            entry.save()
            messages.success(request, f'Saved -- {entry.invoice_number}')
            return redirect(f"{request.path}?date={entry.entry_date.isoformat()}")
        messages.error(request, 'Please fix the errors below.')
    else:
        form = BillingEntryForm(initial={'entry_date': timezone.localdate()})

    date_str = request.GET.get('date', '').strip()
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.localdate()
    except ValueError:
        selected_date = timezone.localdate()

    # Own entries only -- never another physio's, same scoping as
    # personal_account.personal_dashboard's created_by=request.user filter.
    entries = BillingEntry.objects.filter(physio=request.user, entry_date=selected_date)
    total = entries.aggregate(total=Sum('rate'))['total'] or 0

    context = {
        'form': form,
        'entries': entries,
        'selected_date': selected_date,
        'total': total,
        'today': timezone.localdate(),
    }
    return render(request, 'billing/billing_list.html', context)


@login_required
def billing_entry_edit(request, entry_id):
    entry = get_object_or_404(BillingEntry, id=entry_id, physio=request.user)
    if request.method == 'POST':
        form = BillingEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, f'Updated -- {entry.invoice_number}')
            return redirect(f"/billing/?date={entry.entry_date.isoformat()}")
    else:
        form = BillingEntryForm(instance=entry)
    return render(request, 'billing/billing_entry_edit.html', {'form': form, 'entry': entry})


@login_required
def billing_entry_delete(request, entry_id):
    entry = get_object_or_404(BillingEntry, id=entry_id, physio=request.user)
    if request.method == 'POST':
        entry_date = entry.entry_date
        entry.delete()
        messages.success(request, 'Entry deleted.')
        return redirect(f"/billing/?date={entry_date.isoformat()}")
    return redirect('billing-list')


@login_required
def patient_billing_page(request, patient_id):
    """Per-patient subscription packages -- sits alongside the Stat/
    Track/Rx/Exe/Assess action-row buttons (same patient, same row, on
    personal/clinic/enterprise's dashboard and detail templates).

    Distinct from BillingEntry/billing_list above: that's a free-text
    daily paper-log replacement with no patient FK; this tracks real
    session usage against a real AddPatient, incremented from
    prescription_app.views.save_treatment_session whenever a treatment
    session is logged for this patient while a package here is active."""
    patient = get_object_or_404(AddPatient, id=patient_id)

    if request.method == 'POST':
        form = PatientPackageForm(request.POST)
        if form.is_valid():
            package = form.save(commit=False)
            package.patient = patient
            package.physio = request.user
            package.save()
            messages.success(request, f'Package started -- {package.get_duration_display()}, {package.total_sessions} sessions.')
            return redirect('patient-billing', patient_id=patient.id)
        messages.error(request, 'Please fix the errors below.')
    else:
        form = PatientPackageForm(initial={'start_date': timezone.localdate()})

    packages = patient.packages.select_related('physio').all()
    active_package = next((p for p in packages if p.effective_status == 'active'), None)

    context = {
        'patient': patient,
        'form': form,
        'packages': packages,
        'active_package': active_package,
    }
    return render(request, 'billing/patient-billing.html', context)


@login_required
def patient_package_cancel(request, patient_id, package_id):
    package = get_object_or_404(PatientPackage, id=package_id, patient_id=patient_id)
    if request.method == 'POST':
        package.status = 'cancelled'
        package.save()
        messages.success(request, 'Package cancelled.')
    return redirect('patient-billing', patient_id=patient_id)
