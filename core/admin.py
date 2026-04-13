from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Employee,
    Department,
    TimeOffType,
    TimeOffRequest,
    AttendanceRecord,
    ZKTecoDevice,
    Message,
    Asset,
    EmployeeDocument,
)


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    list_display = (
        "full_name",
        "iqama_number",
        "role",
        "job_title",
        "department",
        "employment_status",
    )
    list_filter = ("employment_status", "department", "contract_type", "role")
    search_fields = ("full_name", "iqama_number", "email")
    ordering = ("full_name",)
    fieldsets = None
    fields = None

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {"fields": ("iqama_number", "password", "role")}),
            ("Personal info", {"fields": ("full_name", "email", "mobile_number")}),
            (
                "Permissions",
                {
                    "fields": (
                        "is_active",
                        "is_staff",
                        "is_superuser",
                        "groups",
                        "user_permissions",
                    )
                },
            ),
            ("Important dates", {"fields": ("last_login", "date_joined")}),
        )


admin.site.register(Department)
admin.site.register(TimeOffType)
admin.site.register(TimeOffRequest)
admin.site.register(AttendanceRecord)
admin.site.register(ZKTecoDevice)
admin.site.register(Message)
admin.site.register(Asset)
admin.site.register(EmployeeDocument)
