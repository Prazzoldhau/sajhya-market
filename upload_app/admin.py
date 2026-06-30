from django.contrib import admin
from .models import APKRelease


@admin.register(APKRelease)
class APKReleaseAdmin(admin.ModelAdmin):
    list_display = ['version', 'is_latest', 'uploaded_at', 'file']
    list_editable = ['is_latest']
    readonly_fields = ['uploaded_at']
