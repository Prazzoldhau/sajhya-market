from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path ('', TemplateView.as_view(template_name="index.html"), name='landing'),
    path ('admin/', admin.site.urls),
    path ('', include('main.urls')),
    path ('acc/', include ('account_app.urls')),
    path ('personal-acc/', include ('personal_account.urls')),
    path ('clinic-acc/', include('clinic_account.urls')),
    path ('enterprise-acc/', include('enterprise_account.urls')),
    path ('exercise-app/', include('exercise_app.urls')),
    path ('detail-app/', include('detail_app.urls')),
    path ('video-app/', include('video_app.urls')),
    path ('prescription-app/', include('prescription_app.urls')),
    path ('patient-app/', include('patient_app.urls')),
    path ('upload-app/', include('upload_app.urls')),
    path ('referral/', include('referral_app.urls')),
    path ('marketplace/', include('marketplace_app.urls')),
    path ('find-physio/', include('find_physio_app.urls')),
    path ('summit/', include('summit_app.urls')),
    path ('visit-notes/', include('visit_notes_app.urls')),
    path ('physio-api/', include('physio_api_app.urls')),

]

# Only serve media files in development (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)