from django.contrib import admin

from .models import AppOpenEvent, VideoClickEvent


@admin.register(AppOpenEvent)
class AppOpenEventAdmin(admin.ModelAdmin):
    list_display = ['patient', 'opened_on', 'ping_count', 'first_opened_at']
    list_filter = ['opened_on']
    search_fields = ['patient__patient_name', 'patient__patient_code']
    date_hierarchy = 'opened_on'


@admin.register(VideoClickEvent)
class VideoClickEventAdmin(admin.ModelAdmin):
    list_display = ['exercise_name', 'prescription_exercise', 'clicked_at']
    list_filter = ['clicked_at']
    search_fields = ['exercise_name', 'prescription_exercise__prescription__patient__patient_name']
    date_hierarchy = 'clicked_at'
