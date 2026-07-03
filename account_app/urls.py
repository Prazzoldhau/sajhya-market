from django.urls import path
from .import views



urlpatterns = [
    path ('package/', views.package_load, name = 'package_page'),
    path ('signup-personal/', views.signup_personal, name = 'signup-personal'),
    path ('signup-clinic/', views.signup_clinic, name = 'signup-clinic'),
    path ('signup-enterprise/', views.signup_enterprise, name = 'signup-enterprise'),
    path ('login/', views.login_view, name = 'login'),
    path ('login-personal/', views.login_view_personal, name = 'login-personal'),
    path ('login-clinic/', views.login_view_clinic, name = 'login-clinic'),
    path ('login-enterprise/', views.login_view_enterprise, name = 'login-enterprise'),
    path ('logout-clinic/', views.logout_view_clinic, name = 'logout-clinic'),
    path ('logout-personal/', views.logout_view_personal, name = 'logout-personal'),
    path ('logout-enterprise/', views.logout_view_enterprise, name = 'logout-enterprise'),
    path ('reset/', views.password_reset_view, name = 'password_reset_page'),
    path ('login-signup-clinic/', views.login_signup_clinic, name='login-signup-clinic'),
    path ('login-signup-personal/', views.login_signup_personal, name='login-signup-personal'),
    path ('login-signup-enterprise/', views.login_signup_enterprise, name='login-signup-enterprise'),
    path ('password-reset/', views.password_reset_view, name = 'password_reset_page'),
    path ('patientlistdashboard/', views.patientlist_dashboard, name='patientlist-dashboard'),
    path ('index/', views.landing_page, name = "landing-page"),
]
