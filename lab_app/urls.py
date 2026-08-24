from django.urls import path
from . import views

urlpatterns = [
    path('', views.lab_tests, name='lab-tests'),
    path('test/<int:test_id>/', views.lab_test_detail, name='lab-test-detail'),
    path('panel/<int:panel_id>/', views.lab_panel_detail, name='lab-panel-detail'),
    path('add-to-cart/<str:item_type>/<int:item_id>/', views.lab_add_to_cart, name='lab-add-to-cart'),
    path('remove-from-cart/<str:item_type>/<int:item_id>/', views.lab_remove_from_cart, name='lab-remove-from-cart'),
    path('cart/', views.lab_view_cart, name='lab-view-cart'),
    path('checkout/', views.lab_checkout, name='lab-checkout'),
    path('order-success/<str:order_number>/', views.lab_order_success, name='lab-order-success'),
]
