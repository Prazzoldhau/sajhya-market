from django.urls import path
from . import views


urlpatterns = [
    path('patient-login/', views.patient_login, name='patient-login'),
    path('patient-dashboard/', views.patient_dashboard, name='patient-dashboard'),

    # Auth
    path('api/csrf/', views.csrf_token_view, name='csrf_token'),
    path('api/login/', views.patient_api_login, name='patient_api_login'),
    path('api/qr-login/', views.patient_api_qr_login, name='patient_api_qr_login'),
    path('api/logout/', views.patient_api_logout, name='patient_api_logout'),
    path('api/me/', views.patient_api_me, name='patient_api_me'),

    # Push notifications
    path('sw.js', views.patient_service_worker, name='patient-service-worker'),
    path('api/push/subscribe/', views.patient_api_push_subscribe, name='patient_api_push_subscribe'),

    # Exercises
    path('api/exercise/<int:exercise_id>/feedback/', views.submit_exercise_feedback, name='submit_exercise_feedback'),

    # Marketplace
    path('api/categories/', views.patient_api_categories, name='patient_api_categories'),
    path('api/products/', views.patient_api_products, name='patient_api_products'),
    path('api/cart/', views.patient_api_cart, name='patient_api_cart'),
    path('api/cart/add/<int:product_id>/', views.patient_api_cart_add, name='patient_api_cart_add'),
    path('api/cart/update/', views.patient_api_cart_update, name='patient_api_cart_update'),
    path('api/order/', views.patient_api_order, name='patient_api_order'),
    path('api/orders/', views.patient_api_orders, name='patient_api_orders'),
    path('api/physio/', views.patient_api_physio, name='patient_api_physio'),
    path('api/recommended/', views.patient_api_recommended, name='patient_api_recommended'),
    path('add-recs-to-cart/', views.add_recs_to_cart, name='add-recs-to-cart'),
]
