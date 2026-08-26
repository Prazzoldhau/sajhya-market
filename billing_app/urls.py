from django.urls import path
from . import views

urlpatterns = [
    path('', views.billing_list, name='billing-list'),
    path('entry/<int:entry_id>/edit/', views.billing_entry_edit, name='billing-entry-edit'),
    path('entry/<int:entry_id>/delete/', views.billing_entry_delete, name='billing-entry-delete'),
]
