from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import SessionSubmission, Table


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ["number", "label", "created_at"]


class SessionSubmissionResource(resources.ModelResource):
    class Meta:
        model = SessionSubmission
        fields = ("id", "table", "session_key", "facilitator_name", "is_complete", "submitted_at", "current_step", "data")


@admin.register(SessionSubmission)
class SessionSubmissionAdmin(ImportExportModelAdmin):
    resource_class = SessionSubmissionResource
    list_display = ["table", "session_key", "facilitator_name", "is_complete", "current_step", "submitted_at"]
    list_filter = ["session_key", "is_complete"]
    search_fields = ["facilitator_name", "table__label"]
    readonly_fields = ["created_at", "updated_at"]
