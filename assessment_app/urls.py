from django.urls import path
from . import views

urlpatterns = [
    path('patient/<int:patient_id>/assessments/', views.assessment_list, name='assessment-list'),
    path('patient/<int:patient_id>/assessments/add/', views.create_assessment, name='create-assessment'),
    path('assessment/<int:assessment_id>/', views.assessment_detail, name='assessment-detail'),
    path('assessment/<int:assessment_id>/edit/', views.edit_assessment, name='edit-assessment'),
]
