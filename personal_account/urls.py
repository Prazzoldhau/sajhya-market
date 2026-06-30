from django.urls import path
from .import views

urlpatterns = [
    path ('create-patient/', views.create_patient, name = 'create-patient'),
    path ('personal-dashboard/', views.personal_dashboard, name = 'personal-dashboard'),
    path ('assigned-clinic-dashboard/<int:clinic_id>/', views.assigned_clinic_dashboard, name= "assigned-clinic-dashboard"),
    path ('my-clinics/', views.get_my_clinics, name='my-clinics'),
    path ('add-patient-to-clinic/<int:clinic_id>/', views.add_patient_to_clinic, name="add-patient-to-clinic"),
    
]
