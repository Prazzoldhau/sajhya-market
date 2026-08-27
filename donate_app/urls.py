from django.urls import path
from . import views

urlpatterns = [
    path('', views.donate, name='donate'),
    path('success/<str:pledge_number>/', views.donate_success, name='donate-success'),
]
