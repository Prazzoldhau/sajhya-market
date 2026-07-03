from django.urls import path
from . import views

urlpatterns = [
    path('onboarding/', views.enterprise_onboarding, name='enterprise-onboarding'),
    path('dashboard/', views.enterprise_dashboard, name='enterprise-dashboard'),

    path('departments/', views.department_list, name='department-list'),
    path('departments/create/', views.department_create, name='department-create'),
    path('departments/<int:department_id>/', views.department_detail, name='department-detail'),

    path('staff/', views.staff_list, name='staff-list'),
    path('staff/assign/', views.staff_assign, name='staff-assign'),
    path('staff/search-users/', views.search_enterprise_users, name='search-enterprise-users'),

    path('modules/inpatient-referral/', views.module_stub, {'module_key': 'inpatient-referral'}, name='enterprise-module-inpatient-referral'),
    path('modules/usg-reporting/', views.module_stub, {'module_key': 'usg-reporting'}, name='enterprise-module-usg-reporting'),
    path('modules/queue-management/', views.module_stub, {'module_key': 'queue-management'}, name='enterprise-module-queue-management'),
    path('modules/requisition-form/', views.module_stub, {'module_key': 'requisition-form'}, name='enterprise-module-requisition-form'),
    path('modules/maintenance-request/', views.module_stub, {'module_key': 'maintenance-request'}, name='enterprise-module-maintenance-request'),
]
