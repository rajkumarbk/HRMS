from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    # Employees
    path("employees/", views.employee_list, name="employee_list"),
    path("employees/create/", views.employee_create, name="employee_create"),
    path("employees/<int:pk>/", views.employee_detail, name="employee_detail"),
    path(
        "employees/<int:pk>/documents/",
        views.employee_documents,
        name="employee_documents",
    ),
    path("documents/delete/<int:pk>/", views.delete_document, name="delete_document"),
    # Time Off
    path("timeoff/", views.timeoff_list, name="timeoff_list"),
    path("timeoff/create/", views.timeoff_create, name="timeoff_create"),
    path("timeoff/<int:pk>/approve/", views.timeoff_approve, name="timeoff_approve"),
    path("timeoff/<int:pk>/refuse/", views.timeoff_refuse, name="timeoff_refuse"),
    path("timeoff/<int:pk>/reset/", views.timeoff_reset, name="timeoff_reset"),
    # Attendance
    path("attendance/", views.attendance_list, name="attendance_list"),
    path(
        "attendance/sync/<int:device_id>/",
        views.attendance_sync,
        name="attendance_sync",
    ),
    path("attendance/device/add/", views.device_add, name="device_add"),
    path("attendance/devices/<int:pk>/", views.device_detail, name="device_detail"),
    path("my-attendance/", views.my_attendance, name="my_attendance"),
    # Discuss
    path("discuss/", views.discuss, name="discuss"),
    # User Account URLs
    path("users/", views.user_accounts, name="user_accounts"),
    path("users/create/", views.create_user_account, name="create_user_account"),
    path(
        "users/reset-password/", views.reset_user_password, name="reset_user_password"
    ),
    path(
        "users/toggle-status/<int:pk>/",
        views.toggle_user_status,
        name="toggle_user_status",
    ),
    path(
        "users/change-role/<int:pk>/<str:role>/",
        views.change_user_role,
        name="change_user_role",
    ),
    # Asset URLs
    path("assets/", views.asset_handover_list, name="asset_handover_list"),
    path("assets/handover/", views.asset_handover, name="asset_handover"),
    path("assets/return/", views.asset_return, name="asset_return"),
    path("attendance/devices/add/", views.device_add, name="device_add"),
    path("attendance/devices/<int:pk>/", views.device_detail, name="device_detail"),
    path("attendance/devices/<int:pk>/sync/", views.device_sync, name="device_sync"),
    path(
        "attendance/devices/<int:pk>/report/csv/",
        views.attendance_report_csv,
        name="attendance_report_csv",
    ),
    path('advance-salary/', views.advance_salary_list, name='advance_salary_list'),
    path('advance-salary/create/', views.advance_salary_create, name='advance_salary_create'),
    path('advance-salary/<int:pk>/review/', views.advance_salary_review, name='advance_salary_review'),
    path('advance-salary/<int:pk>/approve/', views.advance_salary_approve, name='advance_salary_approve'),
    path('advance-salary/<int:pk>/refuse/', views.advance_salary_refuse, name='advance_salary_refuse'),
    path('advance-salary/<int:pk>/delete/', views.advance_salary_delete, name='advance_salary_delete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
