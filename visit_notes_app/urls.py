from django.urls import path
from . import views

urlpatterns = [
    path('patient/<int:patient_id>/notes/', views.visit_notes_list, name='visit-notes-list'),
    path('patient/<int:patient_id>/notes/add/', views.create_visit_note, name='create-visit-note'),
    path('note/<int:note_id>/', views.visit_note_detail, name='visit-note-detail'),
    path('note/<int:note_id>/edit/', views.edit_visit_note, name='edit-visit-note'),
]
