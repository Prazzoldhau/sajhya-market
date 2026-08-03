from django.urls import path
from . import views

urlpatterns = [
    # auth
    path('csrf/',   views.vendor_csrf,  name='vendor-csrf'),
    path('login/',  views.vendor_login, name='vendor-login'),
    path('logout/', views.vendor_logout, name='vendor-logout'),
    path('me/',     views.vendor_me,    name='vendor-me'),

    # orders
    path('orders/',                          views.order_list,          name='vendor-order-list'),
    path('orders/<str:order_number>/',        views.order_detail,        name='vendor-order-detail'),
    path('orders/<str:order_number>/status/', views.order_update_status, name='vendor-order-status'),
]
