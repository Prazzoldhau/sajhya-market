from django.urls import path
from . import views

urlpatterns = [
    path('', views.lab_tests, name='lab-tests'),
    path('test/<int:test_id>/', views.lab_test_detail, name='lab-test-detail'),
    path('panel/<int:panel_id>/', views.lab_panel_detail, name='lab-panel-detail'),
    path('order-success/<str:request_number>/', views.lab_order_success, name='lab-order-success'),
]
