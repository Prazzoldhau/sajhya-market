from django.urls import path
from . import views

urlpatterns = [
    path('', views.billing_list, name='billing-list'),
    path('entry/<int:entry_id>/edit/', views.billing_entry_edit, name='billing-entry-edit'),
    path('entry/<int:entry_id>/delete/', views.billing_entry_delete, name='billing-entry-delete'),
    path('patient/<int:patient_id>/', views.patient_billing_page, name='patient-billing'),
    path('patient/<int:patient_id>/package/<int:package_id>/cancel/', views.patient_package_cancel, name='patient-package-cancel'),
    path('patient/<int:patient_id>/package/<int:package_id>/payment/', views.patient_package_payment, name='patient-package-payment'),
]
