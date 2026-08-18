from django.urls import path
from . import views


urlpatterns = [
    path('patient-login/', views.patient_login, name='patient-login'),
    path('patient-dashboard/', views.patient_dashboard, name='patient-dashboard'),

    # Auth
    path('api/csrf/', views.csrf_token_view, name='csrf_token'),
    path('api/login/', views.patient_api_login, name='patient_api_login'),
    path('api/signup/', views.patient_api_signup, name='patient_api_signup'),
    path('api/qr-login/', views.patient_api_qr_login, name='patient_api_qr_login'),
    path('api/logout/', views.patient_api_logout, name='patient_api_logout'),
    path('api/me/', views.patient_api_me, name='patient_api_me'),
    path('api/activate/', views.patient_api_activate, name='patient_api_activate'),
    path('api/pair-physio/', views.patient_api_pair_physio, name='patient_api_pair_physio'),
    path('api/delete-account/', views.patient_api_delete_account, name='patient_api_delete_account'),

    # Public, no-login-required deletion page. Google Play requires a deletion
    # route reachable from a browser without installing the app; this URL goes
    # in the Play Console Data Safety form.
    path('delete-account/', views.patient_delete_account_web, name='patient-delete-account-web'),

    # Public privacy policy. Its URL is mandatory on the Play Store listing and
    # in the Data Safety form for an app handling health data.
    path('privacy-policy/', views.patient_privacy_policy, name='patient-privacy-policy'),

    # Push notifications
    path('sw.js', views.patient_service_worker, name='patient-service-worker'),
    path('api/push/subscribe/', views.patient_api_push_subscribe, name='patient_api_push_subscribe'),

    # Exercises
    path('api/exercise/<int:exercise_id>/feedback/', views.submit_exercise_feedback, name='submit_exercise_feedback'),
    path('api/exercise/<int:exercise_id>/video-click/', views.submit_video_click, name='submit_video_click'),

    # Engagement tracking
    path('api/ping-open/', views.patient_api_ping_open, name='patient_api_ping_open'),

    # Marketplace
    path('api/categories/', views.patient_api_categories, name='patient_api_categories'),
    path('api/products/', views.patient_api_products, name='patient_api_products'),
    path('api/pharmacy/products/', views.patient_api_pharmacy_products, name='patient_api_pharmacy_products'),
    path('api/cart/', views.patient_api_cart, name='patient_api_cart'),
    path('api/cart/add/<int:product_id>/', views.patient_api_cart_add, name='patient_api_cart_add'),
    path('api/cart/update/', views.patient_api_cart_update, name='patient_api_cart_update'),
    path('api/order/', views.patient_api_order, name='patient_api_order'),
    path('api/orders/', views.patient_api_orders, name='patient_api_orders'),
    path('api/physio/', views.patient_api_physio, name='patient_api_physio'),
    path('api/recommended/', views.patient_api_recommended, name='patient_api_recommended'),
    path('add-recs-to-cart/', views.add_recs_to_cart, name='add-recs-to-cart'),

    # Lab service (Blood Investigation)
    path('api/lab/tests/', views.patient_api_lab_tests, name='patient_api_lab_tests'),
    path('api/lab/request/', views.patient_api_lab_request_create, name='patient_api_lab_request_create'),
    path('api/lab/requests/', views.patient_api_lab_requests, name='patient_api_lab_requests'),
]
