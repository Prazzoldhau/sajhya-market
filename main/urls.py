from django.urls import path
from .import views

urlpatterns = [
    path ('index/', views.landing_page, name='landing_page'),
]
