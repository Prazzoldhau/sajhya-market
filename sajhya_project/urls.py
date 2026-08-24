from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from main.views import landing_page, robots_txt
from main.sitemaps import StaticViewSitemap, ProductSitemap, PharmacyProductSitemap, LabTestSitemap, LabTestPanelSitemap, VacancySitemap

sitemaps = {
    'static': StaticViewSitemap,
    'products': ProductSitemap,
    'pharmacy-products': PharmacyProductSitemap,
    'lab-tests': LabTestSitemap,
    'lab-panels': LabTestPanelSitemap,
    'vacancies': VacancySitemap,
}

urlpatterns = [
    path ('', landing_page, name='landing'),
    path ('robots.txt', robots_txt, name='robots-txt'),
    path ('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
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
    path ('careers/', include('careers_app.urls')),
    path ('find-physio/', include('find_physio_app.urls')),
    path ('summit/', include('summit_app.urls')),
    path ('visit-notes/', include('visit_notes_app.urls')),
    path ('physio-api/', include('physio_api_app.urls')),
    path ('vendor-api/', include('vendor_api_app.urls')),
    path ('delivery/', include('delivery_app.urls')),

]

# Only serve media files in development (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)