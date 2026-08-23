from django.contrib import admin
from django.utils.html import format_html
from .models import Vacancy, VacancyApplication


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'location', 'employment_type', 'is_active', 'closing_date', 'posted_at', 'application_count']
    list_filter = ['is_active', 'employment_type', 'department']
    search_fields = ['title', 'department', 'location']
    list_editable = ['is_active']

    def application_count(self, obj):
        return obj.applications.count()
    application_count.short_description = 'Applications'


class ApplicationVacancyFilter(admin.SimpleListFilter):
    title = 'vacancy'
    parameter_name = 'vacancy'

    def lookups(self, request, model_admin):
        return [(v.id, v.title) for v in Vacancy.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(vacancy_id=self.value())
        return queryset


@admin.register(VacancyApplication)
class VacancyApplicationAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'vacancy', 'email', 'whatsapp_number', 'status', 'applied_at', 'resume_link', 'whatsapp_button']
    list_filter = ['status', ApplicationVacancyFilter]
    list_editable = ['status']
    search_fields = ['full_name', 'email', 'whatsapp_number']
    readonly_fields = ['vacancy', 'full_name', 'email', 'whatsapp_number', 'resume', 'cover_note', 'applied_at', 'whatsapp_button']
    fields = ['vacancy', 'full_name', 'email', 'whatsapp_number', 'whatsapp_button', 'resume', 'cover_note', 'status', 'admin_notes', 'applied_at']

    def resume_link(self, obj):
        if obj.resume:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.resume.url)
        return '—'
    resume_link.short_description = 'Resume'

    def whatsapp_button(self, obj):
        if obj.whatsapp_link:
            return format_html('<a href="{}" target="_blank" style="white-space:nowrap">💬 Message on WhatsApp</a>', obj.whatsapp_link)
        return '—'
    whatsapp_button.short_description = 'WhatsApp'
