from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.rider_dashboard, name='rider-dashboard'),
    path('toggle-availability/', views.toggle_availability, name='rider-toggle-availability'),
    path('<int:delivery_id>/status/', views.update_delivery_status, name='rider-update-delivery-status'),
]
