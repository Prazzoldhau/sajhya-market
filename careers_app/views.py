import logging

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Vacancy, VacancyApplication

logger = logging.getLogger(__name__)


def vacancy_list(request):
    vacancies = Vacancy.objects.filter(is_active=True)

    search = request.GET.get('search', '').strip()
    if search:
        vacancies = vacancies.filter(title__icontains=search)

    context = {
        'vacancies': vacancies,
        'search': search,
    }
    return render(request, 'careers/vacancy_list.html', context)


def vacancy_detail(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk, is_active=True)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        whatsapp_number = request.POST.get('whatsapp_number', '').strip()
        cover_note = request.POST.get('cover_note', '').strip()
        resume = request.FILES.get('resume')

        if not full_name or not email:
            messages.error(request, 'Name and email are required.')
        else:
            application = VacancyApplication.objects.create(
                vacancy=vacancy,
                full_name=full_name,
                email=email,
                whatsapp_number=whatsapp_number,
                cover_note=cover_note,
                resume=resume,
            )
            _send_application_emails(application)
            return redirect('application-success', pk=application.pk)

    context = {'vacancy': vacancy}
    return render(request, 'careers/vacancy_detail.html', context)


def application_success(request, pk):
    application = get_object_or_404(VacancyApplication, pk=pk)
    return render(request, 'careers/application_success.html', {'application': application})


def _send_application_emails(application):
    """Best-effort -- EMAIL_BACKEND isn't configured yet (no SMTP creds in
    settings/.env), so send_mail will fail until that's set up. Caught here
    so a broken/unconfigured mail server never blocks the application itself
    from saving; the applicant still gets the on-screen confirmation either
    way. See HR_NOTIFICATION_EMAIL in settings for who gets notified of new
    applications."""
    applicant_subject = f"We've received your application — {application.vacancy.title}"
    applicant_body = (
        f"Hi {application.full_name},\n\n"
        f"Thanks for applying to Sajhya for the {application.vacancy.title} role. "
        f"We've received your application and will reach out by email"
        + (" or WhatsApp" if application.whatsapp_number else "")
        + " if you're shortlisted.\n\n— Sajhya"
    )

    hr_subject = f"New application: {application.vacancy.title} — {application.full_name}"
    hr_body = (
        f"{application.full_name} applied for {application.vacancy.title}.\n\n"
        f"Email: {application.email}\n"
        f"WhatsApp: {application.whatsapp_number or '—'}\n"
        f"Resume: {'attached in admin' if application.resume else 'not provided'}\n\n"
        f"Cover note:\n{application.cover_note or '—'}\n\n"
        f"Review: {getattr(settings, 'SITE_URL', '')}/admin/careers_app/vacancyapplication/{application.pk}/change/"
    )

    # EMAIL_HOST being empty means SMTP was never configured (see settings.py) --
    # skip the attempt entirely rather than opening a connection that's
    # guaranteed to fail and logging an exception on every single application.
    if not getattr(settings, 'EMAIL_HOST', ''):
        return

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'HR_NOTIFICATION_EMAIL', None)
    hr_email = getattr(settings, 'HR_NOTIFICATION_EMAIL', None)

    try:
        if from_email:
            send_mail(applicant_subject, applicant_body, from_email, [application.email], fail_silently=False)
    except Exception:
        logger.exception('Failed to send applicant confirmation email for application %s', application.pk)

    try:
        if from_email and hr_email:
            send_mail(hr_subject, hr_body, from_email, [hr_email], fail_silently=False)
    except Exception:
        logger.exception('Failed to send HR notification email for application %s', application.pk)
