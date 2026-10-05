from django.urls import path
from . import views

urlpatterns = [
    path('patient/<int:patient_id>/assessments/', views.assessment_list, name='assessment-list'),
    path('patient/<int:patient_id>/assessments/add/', views.create_assessment, name='create-assessment'),
    path('assessment/<int:assessment_id>/', views.assessment_detail, name='assessment-detail'),
    path('assessment/<int:assessment_id>/edit/', views.edit_assessment, name='edit-assessment'),

    # Standardized scale assessments (Hoehn & Yahr, TUG, Berg Balance, LPAS, NFOG-Q)
    path('patient/<int:patient_id>/scale-assessments/<str:scale>/add/', views.create_scale_assessment, name='create-scale-assessment'),
    path('scale-assessment/<int:assessment_id>/', views.scale_assessment_detail, name='scale-assessment-detail'),
]
