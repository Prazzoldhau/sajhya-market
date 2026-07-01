from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.conf import settings

from account_app.models import User
from clinic_account.models import Clinic
from .models import PhysioProfile, PhysioAvailability, BookingRequest, PhysioReview, Specialization
from .forms import BookingForm, PhysioProfileForm, AvailabilityForm


def find_physio(request):
    q_location = request.GET.get('location', '').strip()
    q_condition = request.GET.get('condition', '').strip()
    q_budget = request.GET.get('budget', '').strip()
    q_spec = request.GET.getlist('spec')
    q_visit = request.GET.get('visit', '').strip()

    profiles = (
        PhysioProfile.objects
        .filter(is_public=True)
        .select_related('physio')
        .prefetch_related('specializations')
    )

    if q_location:
        profiles = profiles.filter(location__icontains=q_location)

    if q_condition:
        profiles = profiles.filter(
            Q(specializations__name__icontains=q_condition) |
            Q(bio__icontains=q_condition)
        ).distinct()

    if q_spec:
        profiles = profiles.filter(specializations__slug__in=q_spec).distinct()

    if q_budget:
        try:
            profiles = profiles.filter(consultation_fee__lte=Decimal(q_budget))
        except InvalidOperation:
            pass

    if q_visit == 'home':
        profiles = profiles.filter(is_home_visit=True)
    elif q_visit == 'clinic':
        profiles = profiles.filter(is_clinic_visit=True)

    profiles = profiles.order_by('-avg_rating', '-total_reviews')
    specializations = Specialization.objects.all()

    context = {
        'profiles': profiles,
        'specializations': specializations,
        'q_location': q_location,
        'q_condition': q_condition,
        'q_budget': q_budget,
        'q_spec': q_spec,
        'q_visit': q_visit,
    }
    return render(request, 'find_physio/find-physio.html', context)


def physio_profile(request, username):
    physio_user = get_object_or_404(User, username=username)
    profile = get_object_or_404(PhysioProfile, physio=physio_user, is_public=True)
    reviews = PhysioReview.objects.filter(physio=physio_user, is_approved=True)
    availability = PhysioAvailability.objects.filter(physio=physio_user)
    clinics = Clinic.objects.filter(
        clinicphysio__physio=physio_user,
        clinicphysio__is_active=True
    )
    context = {
        'profile': profile,
        'physio': physio_user,
        'reviews': reviews,
        'availability': availability,
        'clinics': clinics,
        'star_range': range(1, 6),
    }
    return render(request, 'find_physio/physio-profile.html', context)


def book_physio(request, username):
    physio_user = get_object_or_404(User, username=username)
    profile = get_object_or_404(PhysioProfile, physio=physio_user, is_public=True)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.physio = physio_user
            booking.save()
            return redirect('booking-success', pk=booking.pk)
    else:
        form = BookingForm()

    context = {
        'profile': profile,
        'physio': physio_user,
        'form': form,
    }
    return render(request, 'find_physio/book-physio.html', context)


def booking_success(request, pk):
    booking = get_object_or_404(BookingRequest, pk=pk)
    context = {'booking': booking}
    return render(request, 'find_physio/booking-success.html', context)


@login_required(login_url='/acc/login/')
def manage_profile(request):
    profile, _ = PhysioProfile.objects.get_or_create(physio=request.user)
    availability = PhysioAvailability.objects.filter(physio=request.user)

    if request.method == 'POST':
        form = PhysioProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Public profile updated successfully.')
            return redirect('manage-physio-profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PhysioProfileForm(instance=profile)

    av_form = AvailabilityForm()
    public_url = request.build_absolute_uri(f'/find-physio/{request.user.username}/')
    context = {
        'form': form,
        'profile': profile,
        'availability': availability,
        'av_form': av_form,
        'public_url': public_url,
    }
    return render(request, 'find_physio/manage-profile.html', context)


@login_required(login_url='/acc/login/')
def add_availability(request):
    if request.method == 'POST':
        form = AvailabilityForm(request.POST)
        if form.is_valid():
            av = form.save(commit=False)
            av.physio = request.user
            try:
                av.save()
                messages.success(request, 'Availability slot added.')
            except Exception:
                messages.error(request, 'That slot already exists.')
    return redirect('manage-physio-profile')


@login_required(login_url='/acc/login/')
def delete_availability(request, pk):
    av = get_object_or_404(PhysioAvailability, pk=pk, physio=request.user)
    if request.method == 'POST':
        av.delete()
        messages.success(request, 'Availability slot removed.')
    return redirect('manage-physio-profile')


@login_required(login_url='/acc/login/')
def manage_bookings(request):
    status_filter = request.GET.get('status', '').strip()
    bookings = BookingRequest.objects.filter(physio=request.user)
    if status_filter in ('pending', 'confirmed', 'cancelled', 'completed'):
        bookings = bookings.filter(status=status_filter)
    bookings = bookings.order_by('preferred_date')

    context = {
        'bookings': bookings,
        'status_filter': status_filter,
        'status_choices': BookingRequest.STATUS,
    }
    return render(request, 'find_physio/manage-bookings.html', context)


@login_required(login_url='/acc/login/')
def update_booking(request, pk):
    booking = get_object_or_404(BookingRequest, pk=pk, physio=request.user)
    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        valid = [s[0] for s in BookingRequest.STATUS]
        if new_status in valid:
            booking.status = new_status
            notes = request.POST.get('notes', '').strip()
            if notes:
                booking.notes = notes
            booking.save(update_fields=['status', 'notes'])
            messages.success(request, f'Booking #{pk} updated to {booking.get_status_display()}.')
        else:
            messages.error(request, 'Invalid status.')
    return redirect('manage-bookings')
