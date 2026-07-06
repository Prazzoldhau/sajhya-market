from django.urls import path
from . import views


urlpatterns = [
    path ('enterprise-dashboard/', views.enterprise_dashboard, name = 'enterprise-dashboard'),
    path ('enterprise-user-create-patient/', views.enterprise_user_create_patient, name = "enterprise-user-create-patient"),
    path ('enterprise-create-enterprise', views.enterprise_create, name ="enterprise-create-enterprise"),
    path ('search-staff/<int:pk>', views.search_staff, name = "search-staff" ),
    path ('enterprise-sub-dash/', views.enterprise_list, name = "enterprise-sub-dash"),
    path ('enterprise-staff-dashboard/', views.staff_list, name = "enterprise-staff-dashboard"),
    path ('claim-staff/', views.claim_staff, name = "claim-staff"),
    path ('enterprise-detail/<int:enterprise_id>/', views.enterprise_detail, name='enterprise-detail'),
    path ('add-patient-by-enterpriseuser/<int:enterprise_id>,', views.add_patient_by_enterpriseuser, name="add-patient-by-enterpriseuser"),
    path ('enterprise-detail/<int:enterprise_id>/add-ward/', views.add_ward, name="add-ward"),
    path ('ward/<str:token>/manifest.json', views.ward_manifest, name='ward-manifest'),
    path ('ward/<str:token>/sw.js', views.ward_service_worker, name='ward-service-worker'),
    path ('ward/<str:token>/', views.ward_login, name='ward-login'),
    path ('ward/<str:token>/logout/', views.ward_logout, name='ward-logout'),
    path ('ward/<str:token>/request/', views.ward_request_form, name='ward-request-form'),
    path ('physio-requests/', views.physio_requests_queue, name='physio-requests-queue'),
    path ('physio-requests/<int:request_id>/handled/', views.mark_request_handled, name='mark-request-handled'),
]
