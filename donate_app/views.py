from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .models import DonatableCategory, DonationPledge


def donate(request):
    if request.method == 'POST':
        return _handle_pledge(request)

    categories = DonatableCategory.objects.filter(is_active=True)
    return render(request, 'donate/donate.html', {'categories': categories})


def _handle_pledge(request):
    donor_name = request.POST.get('donor_name', '').strip()
    phone_number = request.POST.get('phone_number', '').strip()
    address = request.POST.get('address', '').strip()
    notes = request.POST.get('notes', '').strip()
    item_ids = request.POST.getlist('items')

    if not all([donor_name, phone_number, address]):
        messages.error(request, 'Please fill in your name, phone number, and address.')
        return redirect('donate')

    # Not requiring at least one checked item -- someone donating something
    # that isn't in the category list yet should still be able to describe
    # it in notes rather than being blocked from submitting at all.
    if not item_ids and not notes:
        messages.error(request, 'Select at least one item, or describe what you\'re donating in the notes.')
        return redirect('donate')

    pledge = DonationPledge.objects.create(
        donor_name=donor_name,
        phone_number=phone_number,
        address=address,
        notes=notes,
    )
    if item_ids:
        pledge.items.set(DonatableCategory.objects.filter(id__in=item_ids, is_active=True))

    return redirect('donate-success', pledge_number=pledge.pledge_number)


def donate_success(request, pledge_number):
    pledge = get_object_or_404(DonationPledge, pledge_number=pledge_number)
    return render(request, 'donate/donate_success.html', {'pledge': pledge})
