from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BillingEntryForm
from .models import BillingEntry


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
