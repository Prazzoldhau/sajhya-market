from django.urls import path
from . import views

urlpatterns = [
    path('', views.vacancy_list, name='vacancy-list'),
    path('<int:pk>/', views.vacancy_detail, name='vacancy-detail'),
    path('application/<int:pk>/success/', views.application_success, name='application-success'),
]
