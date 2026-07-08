from django.urls import path
from .import views


urlpatterns = [
    path ('clinic-dashboard/', views.clinic_dashboard, name = 'clinic-dashboard'),
    path ('clinic-user-create-patient/', views.clinic_user_create_patient, name = "clinic-user-create-patient"),
    path ('clinic-create-clinic', views.clinic_create, name ="clinic-create-clinic"),
    path ('search-physio/<int:pk>', views.search_physio, name = "search-physio" ),
    path ('search-physio-list/', views.search_physio_list, name='search-physio-list'),
    path ('clinic-sub-dash/', views.clinic_list, name = "clinic-sub-dash"),
    path ('staff-dashboard/', views.staff_list, name = "staff-dashboard"),
    path ('claim-physio/', views.claim_physio, name = "claim-physio"),
    path ('clinic-detail/<int:clinic_id>/', views.clinic_detail, name='clinic-detail'),
    path ('add-patient-by-clinicuser/<int:clinic_id>,', views.add_patient_by_clinicuser, name="add-patient-by-clinicuser"),

    # Queue management
    path ('clinic-queue/<int:clinic_id>/', views.queue_list, name='clinic-queue'),
    path ('clinic-queue/<int:clinic_id>/add/', views.add_to_queue, name='add-to-queue'),
    path ('clinic-queue/entry/<int:entry_id>/call/', views.call_for_session, name='call-for-session'),
    path ('clinic-queue/entry/<int:entry_id>/complete/', views.complete_queue_entry, name='complete-queue-entry'),
]
