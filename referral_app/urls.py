from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_referrals, name='my-referrals'),
    path('create/', views.create_referral, name='create-referral'),
    path('search/', views.search_referral, name='search-referral'),
    path('<str:referral_code>/', views.referral_detail, name='referral-detail'),
    path('<str:referral_code>/update-status/', views.update_referral_status, name='update-referral-status'),
    path('<str:referral_code>/accept/', views.accept_referral, name='accept-referral'),
    path('<str:referral_code>/reject/', views.reject_referral, name='reject-referral'),
]
