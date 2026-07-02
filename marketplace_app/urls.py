from django.urls import path
from . import views

urlpatterns = [
    path('patient/<int:patient_id>/', views.patient_marketplace, name='patient-marketplace'),
    path('patient/<int:patient_id>/recommend/<int:product_id>/', views.add_patient_recommendation, name='add-patient-recommendation'),
    path('recommendation/<int:rec_id>/remove/', views.remove_patient_recommendation, name='remove-patient-recommendation'),
    path('', views.marketplace, name='marketplace'),
    path('product/<int:product_id>/', views.product_detail, name='product-detail'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add-to-cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove-from-cart'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update-cart'),
    path('cart/', views.view_cart, name='view-cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/<str:order_number>/', views.order_success, name='order-success'),
    path('vendor/orders/', views.vendor_orders, name='vendor-orders'),
    path('vendor/orders/<str:order_number>/', views.vendor_order_detail, name='vendor-order-detail'),
]
