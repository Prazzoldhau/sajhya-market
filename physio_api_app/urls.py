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
    path('patients/<str:patient_code>/stats/',   views.patient_stats,                name='physio-patient-stats'),

    # clinics
    path('clinics/',                             views.clinic_list,                  name='physio-clinic-list'),
    path('clinics/<int:clinic_id>/',             views.clinic_detail,                name='physio-clinic-detail'),

    # home visits (find_physio_app bookings)
    path('home-visits/',                         views.home_visit_list,              name='physio-home-visit-list'),
    path('home-visits/<int:booking_id>/status/', views.home_visit_update_status,     name='physio-home-visit-status'),

    # shop (marketplace_app)
    path('shop/categories/',                     views.shop_category_list,           name='physio-shop-categories'),
    path('shop/products/',                       views.shop_product_list,            name='physio-shop-products'),
    path('shop/orders/',                         views.shop_order_list_create,       name='physio-shop-orders'),

    # exercises
    path('regions/',                             views.region_list,                  name='physio-region-list'),
    path('exercises/',                           views.exercise_list,                name='physio-exercise-list'),

    # prescriptions
    path('prescriptions/<str:patient_code>/',   views.prescription_list_create,     name='physio-prescriptions'),
    path('prescriptions/exercises/<int:prescription_id>/add/', views.prescription_add_exercises, name='physio-prescription-add-exercises'),
    path('prescription-exercises/<int:exercise_id>/toggle/',   views.prescription_exercise_toggle, name='physio-pe-toggle'),
    path('prescription-exercises/<int:exercise_id>/remove/',   views.prescription_exercise_remove, name='physio-pe-remove'),
    path('prescription-exercises/<int:exercise_id>/params/',   views.prescription_exercise_update_params, name='physio-pe-update-params'),

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
