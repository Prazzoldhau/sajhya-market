from django.urls import path
from . import views

urlpatterns = [
    # auth
    path('csrf/',                                views.physio_csrf,                  name='physio-csrf'),
    path('login/',                               views.physio_login,                 name='physio-login'),
    path('logout/',                              views.physio_logout,                name='physio-logout'),
    path('me/',                                  views.physio_me,                    name='physio-me'),

    # patients
    path('patients/',                            views.patient_list,                 name='physio-patient-list'),
    path('patients/<str:patient_code>/',         views.patient_detail,               name='physio-patient-detail'),

    # exercises
    path('regions/',                             views.region_list,                  name='physio-region-list'),
    path('exercises/',                           views.exercise_list,                name='physio-exercise-list'),

    # prescriptions
    path('prescriptions/<str:patient_code>/',   views.prescription_list_create,     name='physio-prescriptions'),

    # sessions
    path('sessions/<str:patient_code>/',        views.session_list_create,          name='physio-sessions'),

    # referrals
    path('referrals/',                           views.referral_list_create,         name='physio-referral-list'),
    path('referrals/search/',                    views.referral_search,              name='physio-referral-search'),
    path('referrals/<str:referral_code>/accept/', views.referral_accept,            name='physio-referral-accept'),
    path('referrals/<str:referral_code>/reject/', views.referral_reject,            name='physio-referral-reject'),

    # dashboard stats
    path('dashboard/',                           views.dashboard_stats,              name='physio-dashboard'),

    # users (for referred_to picker)
    path('users/',                               views.user_list,                    name='physio-user-list'),
]
