from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Referral
from .forms import ReferralForm
from personal_account.models import AddPatient


@login_required
def my_referrals(request):
    """Referrals created (sent) by the current user."""
    referrals = Referral.objects.filter(referred_by=request.user).select_related(
        'referred_to', 'referred_to_clinic', 'patient'
    )
    status_filter = request.GET.get('status')
    if status_filter:
        referrals = referrals.filter(status=status_filter)

    context = {
        'referrals': referrals,
        'status_choices': Referral.STATUS_CHOICES,
        'active_status': status_filter,
    }
    return render(request, 'referral_app/my_referrals.html', context)


@login_required
def create_referral(request):
    if request.method == 'POST':
        form = ReferralForm(request.POST)
        if form.is_valid():
            referral = form.save(commit=False)
            referral.referred_by = request.user
            referral.save()
            messages.success(
                request,
                f'Referral {referral.referral_code} created. Share this code with the receiving physio.'
            )
            return redirect('referral-detail', referral_code=referral.referral_code)
    else:
        form = ReferralForm()

    return render(request, 'referral_app/create_referral.html', {'form': form})


@login_required
def search_referral(request):
    """
    Any logged-in user can search for a referral by its code.
    If found and addressed to them (or unaddressed), they can act on it.
    """
    referral = None
    code = request.GET.get('code', '').strip().upper()

    if code:
        try:
            referral = Referral.objects.select_related(
                'referred_by', 'referred_to', 'referred_to_clinic', 'patient'
            ).get(referral_code=code)
        except Referral.DoesNotExist:
            messages.error(request, f'No referral found with code "{code}".')

    return render(request, 'referral_app/search_referral.html', {
        'referral': referral,
        'searched_code': code,
    })


@login_required
def referral_detail(request, referral_code):
    referral = get_object_or_404(
        Referral.objects.select_related('referred_by', 'referred_to', 'referred_to_clinic', 'patient'),
        referral_code=referral_code,
    )

    # Sender or receiver can view
    is_sender = referral.referred_by == request.user
    is_receiver = referral.referred_to == request.user or referral.referred_to is None

    if not is_sender and not is_receiver:
        messages.error(request, 'You do not have access to this referral.')
        return redirect('search-referral')

    return render(request, 'referral_app/referral_detail.html', {
        'referral': referral,
        'is_sender': is_sender,
        'is_receiver': is_receiver,
    })


@login_required
def update_referral_status(request, referral_code):
    referral = get_object_or_404(Referral, referral_code=referral_code)

    is_sender = referral.referred_by == request.user
    is_receiver = referral.referred_to == request.user or referral.referred_to is None

    if not is_sender and not is_receiver:
        messages.error(request, 'Permission denied.')
        return redirect('my-referrals')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = [s[0] for s in Referral.STATUS_CHOICES]
        if new_status in valid_statuses:
            referral.status = new_status
            referral.save()
            messages.success(request, f'Status updated to "{referral.get_status_display()}".')

    return redirect('referral-detail', referral_code=referral_code)


@login_required
def accept_referral(request, referral_code):
    """Accept referral and create patient record from referral data."""
    referral = get_object_or_404(Referral, referral_code=referral_code)

    # Only the intended receiver (or any user if unaddressed) can accept
    if referral.referred_to and referral.referred_to != request.user:
        messages.error(request, 'Only the assigned physio can accept this referral.')
        return redirect('referral-detail', referral_code=referral_code)

    if referral.status != 'pending':
        messages.error(request, 'This referral has already been processed.')
        return redirect('referral-detail', referral_code=referral_code)

    if referral.patient:
        referral.status = 'accepted'
        referral.save()
        messages.success(request, 'Referral accepted.')
        return redirect('referral-detail', referral_code=referral_code)

    if request.method == 'POST':
        patient_name = request.POST.get('patient_name', referral.patient_name).strip()
        patient_contact = request.POST.get('patient_contact', referral.patient_contact).strip()
        patient_diagnosis = request.POST.get('patient_diagnosis', referral.patient_diagnosis).strip()

        if not patient_name or not patient_diagnosis:
            messages.error(request, 'Patient name and diagnosis are required.')
            return render(request, 'referral_app/accept_referral.html', {'referral': referral})

        patient = AddPatient.objects.create(
            patient_name=patient_name,
            patient_contact=patient_contact or '0000000000',
            patient_diagnosis=patient_diagnosis,
            created_by=request.user,
            origin_clinic=referral.referred_to_clinic,
        )

        referral.patient = patient
        referral.status = 'accepted'
        # If referral was unaddressed, claim it
        if not referral.referred_to:
            referral.referred_to = request.user
        referral.save()

        messages.success(
            request,
            f'Referral accepted. Patient {patient.patient_name} ({patient.patient_code}) added to your dashboard.'
        )
        return redirect('referral-detail', referral_code=referral_code)

    return render(request, 'referral_app/accept_referral.html', {'referral': referral})


@login_required
def reject_referral(request, referral_code):
    referral = get_object_or_404(Referral, referral_code=referral_code)

    if referral.referred_to and referral.referred_to != request.user:
        messages.error(request, 'You cannot reject this referral.')
        return redirect('referral-detail', referral_code=referral_code)

    if referral.status != 'pending':
        messages.error(request, 'Only pending referrals can be rejected.')
        return redirect('referral-detail', referral_code=referral_code)

    if request.method == 'POST':
        referral.status = 'rejected'
        if not referral.referred_to:
            referral.referred_to = request.user
        referral.save()
        messages.warning(request, f'Referral {referral.referral_code} rejected.')
        return redirect('my-referrals')

    return render(request, 'referral_app/reject_referral.html', {'referral': referral})
