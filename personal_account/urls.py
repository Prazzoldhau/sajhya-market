from django.urls import path
from .import views

urlpatterns = [
    path ('create-patient/', views.create_patient, name = 'create-patient'),
    path ('personal-dashboard/', views.personal_dashboard, name = 'personal-dashboard'),
    path ('assigned-clinic-dashboard/<int:clinic_id>/', views.assigned_clinic_dashboard, name= "assigned-clinic-dashboard"),
    path ('my-clinics/', views.get_my_clinics, name='my-clinics'),
    path ('add-patient-to-clinic/<int:clinic_id>/', views.add_patient_to_clinic, name="add-patient-to-clinic"),
    path ('assigned-enterprise-dashboard/<int:enterprise_id>/', views.assigned_enterprise_dashboard, name= "assigned-enterprise-dashboard"),
    path ('my-enterprises/', views.get_my_enterprises, name='my-enterprises'),
    path ('add-patient-to-enterprise/<int:enterprise_id>/', views.add_patient_to_enterprise, name="add-patient-to-enterprise"),

]
