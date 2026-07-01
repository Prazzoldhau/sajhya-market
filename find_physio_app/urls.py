from django.urls import path
from . import views

urlpatterns = [
    path('', views.find_physio, name='find-physio'),
    path('manage/profile/', views.manage_profile, name='manage-physio-profile'),
    path('manage/availability/add/', views.add_availability, name='add-availability'),
    path('manage/availability/<int:pk>/delete/', views.delete_availability, name='delete-availability'),
    path('manage/bookings/', views.manage_bookings, name='manage-bookings'),
    path('manage/bookings/<int:pk>/update/', views.update_booking, name='update-booking'),
    path('booking/<int:pk>/success/', views.booking_success, name='booking-success'),
    path('<str:username>/', views.physio_profile, name='physio-profile'),
    path('<str:username>/book/', views.book_physio, name='book-physio'),
]
