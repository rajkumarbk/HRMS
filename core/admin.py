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
    AdvanceSalaryRequest,
    ZKAttendanceLog,
)


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    model = Employee
    ordering = ['-date_joined']
    list_display = ['full_name', 'iqama_number', 'role', 'job_title', 'department', 'employment_status']
    list_filter = ['role', 'employment_status', 'department', 'gender', 'marital_status']
    search_fields = ['full_name', 'iqama_number', 'employee_id', 'email', 'mobile_number']
    
    fieldsets = (
        ('Account', {'fields': ('iqama_number', 'password', 'role', 'advance_role')}),
        ('Personal Info', {'fields': ('full_name', 'email', 'mobile_number', 'alt_mobile_number', 'nationality', 'date_of_birth', 'place_of_birth', 'gender', 'marital_status', 'number_of_dependents', 'religion', 'personal_photo')}),
        ('Passport & ID', {'fields': ('passport_number', 'passport_expiry', 'iqama_expiry_date', 'profession_per_iqama', 'zkteco_uid')}),
        ('Contact', {'fields': ('current_address', 'city', 'country', 'emergency_contact_name', 'emergency_relationship', 'emergency_contact_number')}),
        ('Work Information', {'fields': ('employee_id', 'job_title', 'department', 'branch', 'hiring_date', 'direct_manager', 'work_location', 'employment_status', 'reason_for_termination', 'working_days', 'working_hours', 'work_system', 'work_start_time', 'work_end_time', 'lunch_break_minutes', 'weekly_off_days', 'job_description')}),
        ('Contract', {'fields': ('contract_type', 'contract_duration', 'contract_start', 'contract_end', 'probation_period')}),
        ('Financial', {'fields': ('social_insurance_number', 'bank_account_iban', 'bank_name', 'basic_salary', 'housing_allowance', 'proficiency_allowance', 'other_allowances', 'salary_payment_method', 'salary_payment_date')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('iqama_number', 'full_name', 'password1', 'password2', 'role'),
        }),
    )
    
    filter_horizontal = ('groups', 'user_permissions',)


# Register other models with proper admin
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    search_fields = ['name']


@admin.register(TimeOffType)
class TimeOffTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'days_allowed', 'color']


@admin.register(TimeOffRequest)
class TimeOffRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'date_from', 'date_to', 'approval_state', 'status']
    list_filter = ['approval_state', 'status', 'leave_type']
    search_fields = ['employee__full_name', 'reason']
    raw_id_fields = ['employee', 'approved_by']


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'source']
    list_filter = ['source', 'date']
    search_fields = ['employee__full_name']
    raw_id_fields = ['employee']


@admin.register(ZKTecoDevice)
class ZKTecoDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'ip_address', 'port', 'location', 'is_active', 'connection_status']
    list_filter = ['is_active', 'connection_status']
    search_fields = ['name', 'ip_address', 'location']


@admin.register(ZKAttendanceLog)
class ZKAttendanceLogAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'employee_name', 'punch_time', 'punch_type', 'device']
    list_filter = ['punch_type', 'device']
    search_fields = ['user_id', 'employee_name']
    date_hierarchy = 'punch_time'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'content_preview', 'is_announcement', 'created_at', 'is_read']
    list_filter = ['is_announcement', 'is_read', 'created_at']
    search_fields = ['sender__full_name', 'receiver__full_name', 'content']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'custody_type', 'assigned_to', 'assigned_date', 'is_returned']
    list_filter = ['custody_type', 'is_returned']
    search_fields = ['name', 'serial_number', 'assigned_to__full_name']
    raw_id_fields = ['assigned_to', 'created_by']


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'document_type', 'document_number', 'expiry_date', 'is_expired']
    list_filter = ['document_type']
    search_fields = ['employee__full_name', 'document_number']
    raw_id_fields = ['employee', 'uploaded_by']
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True


@admin.register(AdvanceSalaryRequest)
class AdvanceSalaryRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'amount', 'approval_state', 'status', 'requested_date']
    list_filter = ['approval_state', 'status']
    search_fields = ['employee__full_name', 'reason']
    raw_id_fields = ['employee', 'reviewed_by']