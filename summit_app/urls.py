from django.urls import path

from . import views

urlpatterns = [
    path("", views.choose_table, name="summit-choose-table"),
    path("table/<int:table_number>/login/", views.table_login, name="summit-table-login"),
    path("table/<int:table_number>/logout/", views.table_logout, name="summit-table-logout"),
    path("table/<int:table_number>/leave/", views.leave_table, name="summit-leave-table"),
    path("table/<int:table_number>/", views.table_dashboard, name="summit-table-dashboard"),
    path(
        "table/<int:table_number>/session/<str:session_key>/step/<int:step_no>/",
        views.session_step,
        name="summit-session-step",
    ),
    path("admin/", views.admin_dashboard, name="summit-admin-dashboard"),
    path("admin/table/<int:table_number>/release/", views.release_table, name="summit-release-table"),
    path("admin/table/<int:table_number>/reset/", views.reset_table_sessions, name="summit-reset-table-sessions"),
    path("admin/session/<str:session_key>/", views.admin_session_summary, name="summit-admin-session-summary"),
    path("admin/session/<str:session_key>/live/", views.admin_live_results, name="summit-admin-live-results"),
    path(
        "admin/session/<str:session_key>/live/data/",
        views.admin_live_results_data,
        name="summit-admin-live-results-data",
    ),
]
