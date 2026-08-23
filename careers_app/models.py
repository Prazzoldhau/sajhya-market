from django.db import models


class Vacancy(models.Model):
    EMPLOYMENT_TYPES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    ]

    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=150, default='Kathmandu, Nepal')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default='full_time')
    description = models.TextField(help_text='What the role involves.')
    requirements = models.TextField(blank=True, help_text='One requirement per line -- rendered as a bullet list.')
    is_active = models.BooleanField(default=True, help_text='Untick to close/hide this vacancy without deleting it (past applications stay intact).')
    posted_at = models.DateTimeField(auto_now_add=True)
    closing_date = models.DateField(null=True, blank=True, help_text='Optional -- shown as an "Apply by" date if set.')

    class Meta:
        verbose_name_plural = 'Vacancies'
        ordering = ['-posted_at']

    def __str__(self):
        return self.title

    @property
    def requirements_list(self):
        return [line.strip() for line in self.requirements.splitlines() if line.strip()]


class VacancyApplication(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('reviewing', 'Reviewing'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('hired', 'Hired'),
    ]

    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='applications')
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    whatsapp_number = models.CharField(max_length=20, blank=True, help_text='Include country code, e.g. +9779812345678 -- used for the WhatsApp follow-up link in admin, not sent automatically.')
    resume = models.FileField(upload_to='careers/resumes/%Y/%m/', blank=True, null=True)
    cover_note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    admin_notes = models.TextField(blank=True, help_text='Internal only -- never shown to the applicant.')
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_at']

    def __str__(self):
        return f'{self.full_name} -> {self.vacancy}'

    @property
    def whatsapp_link(self):
        """wa.me deep link pre-filled with a status-update message, for the
        admin to send manually -- there's no WhatsApp Business API wired up
        (would need a Twilio/Meta Cloud API account), so this is a one-click
        assist rather than an automatic send."""
        digits = ''.join(ch for ch in self.whatsapp_number if ch.isdigit())
        if not digits:
            return ''
        from urllib.parse import quote
        message = f"Hi {self.full_name}, this is Sajhya regarding your application for {self.vacancy.title}."
        return f'https://wa.me/{digits}?text={quote(message)}'
