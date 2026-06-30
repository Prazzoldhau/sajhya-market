from django.urls import path
from .import views
urlpatterns = [
    path ('tutorial/', views.load_tutorial, name = "tutorial"),
]
