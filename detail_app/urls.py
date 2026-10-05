from django.urls import path
from .import views


urlpatterns = [
    path ('patient-detail/<int:patient_id>/', views.patient_detail, name = "patient-detail"),
    path ('patient-exericse-status/<int:patient_id>/', views.patient_exercise_status, name="patient-exercise-status"),
    path ('api/exercise/<int:exercise_id>/toggle-completion/', views.toggle_exercise_completion, name='toggle_exercise_completion'),
    path ('api/exercise/<int:exercise_id>/update-params/', views.update_exercise_params, name='update_exercise_params'),
    path ('api/exercise/<int:exercise_id>/remove/', views.remove_prescription_exercise, name='remove_prescription_exercise'),
    path ('reassign-exercise/<int:patient_id>/latest-prescription/', views.latest_prescription, name='api-latest-prescription'),
    path  ('refer-to/<int:patient_id>', views.refer_to, name = "refer-to"),

    # Physio-facing medical profile editor (same page/models the patient's
    # own view edits -- see patient_app.patient_medical_profile_page)
    path('patient/<int:patient_id>/medical-profile/', views.physio_medical_profile_page, name='physio-medical-profile'),
    path('patient/<int:patient_id>/medical-profile/medication/add/', views.physio_medication_add, name='physio-medication-add'),
    path('patient/<int:patient_id>/medical-profile/medication/<int:medication_id>/delete/', views.physio_medication_delete, name='physio-medication-delete'),
    path('patient/<int:patient_id>/medical-profile/bloodtest/add/', views.physio_bloodtest_add, name='physio-bloodtest-add'),
    path('patient/<int:patient_id>/medical-profile/bloodtest/<int:bloodtest_id>/delete/', views.physio_bloodtest_delete, name='physio-bloodtest-delete'),
    path('patient/<int:patient_id>/medical-profile/aid/add/', views.physio_aid_add, name='physio-aid-add'),
    path('patient/<int:patient_id>/medical-profile/aid/<int:aid_id>/delete/', views.physio_aid_delete, name='physio-aid-delete'),
    path('patient/<int:patient_id>/medical-profile/assessment-entry/add/', views.physio_assessment_entry_add, name='physio-assessment-entry-add'),
    path('patient/<int:patient_id>/medical-profile/assessment-entry/<int:entry_id>/delete/', views.physio_assessment_entry_delete, name='physio-assessment-entry-delete'),
    path('patient/<int:patient_id>/medical-profile/diet/add/', views.physio_diet_add, name='physio-diet-add'),
    path('patient/<int:patient_id>/medical-profile/diet/<int:diet_id>/delete/', views.physio_diet_delete, name='physio-diet-delete'),
]
