from django import forms
from django.contrib.auth import authenticate
from django_countries.widgets import CountrySelectWidget
from .models import Employee, EmployeeDocument, TimeOffRequest, ZKTecoDevice, Message


class LoginForm(forms.Form):
    iqama_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={"placeholder": "Iqama / ID Number", "autocomplete": "off"}
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )

    def clean(self):
        cleaned = super().clean()
        iqama = cleaned.get("iqama_number")
        password = cleaned.get("password")
        if iqama and password:
            user = authenticate(iqama_number=iqama, password=password)
            if not user:
                raise forms.ValidationError("Invalid Iqama number or password.")
            cleaned["user"] = user
        return cleaned


class EmployeeBasicForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "full_name",
            "iqama_number",
            "nationality",
            "date_of_birth",
            "place_of_birth",
            "gender",
            "marital_status",
            # "number_of_dependents",
            "religion",
            "personal_photo",
            "passport_number",
            "passport_expiry",
            "zkteco_uid",
        ]


class EmployeeContactForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "mobile_number",
            "alt_mobile_number",
            "email",
            "current_address",
            "city",
            "country",
            "emergency_contact_name",
            "emergency_relationship",
            "emergency_contact_number",
        ]
        widgets = {
            "country": CountrySelectWidget(),
        }


class EmployeeWorkForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "employee_id",
            "job_title",
            "department",
            "branch",
            "hiring_date",
            "contract_type",
            "contract_duration",
            "contract_start",
            "contract_end",
            "probation_period",
            "direct_manager",
            "advance_role",
            "work_location",
            "employment_status",
            "reason_for_termination",
            "working_days",
            "working_hours",
            "work_system",
            "work_start_time",
            "work_end_time",
            "lunch_break_minutes",
            "weekly_off_days",
            "job_description",
        ]


class EmployeeFinancialForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "social_insurance_number",
            "bank_account_iban",
            "bank_name",
            "iqama_expiry_date",
            "profession_per_iqama",
            "basic_salary",
            "housing_allowance",
            "proficiency_allowance",
            "other_allowances",
            "salary_payment_method",
            "salary_payment_date",
        ]


class EmployeeDocumentForm(forms.ModelForm):
    class Meta:
        model = EmployeeDocument
        fields = [
            "document_type",
            "document_number",
            "issue_date",
            "expiry_date",
            "document_file",
            "notes",
        ]
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }


class TimeOffRequestForm(forms.ModelForm):
    class Meta:
        model = TimeOffRequest
        fields = ["leave_type", "date_from", "date_to", "reason"]
        widgets = {
            "date_from": forms.DateInput(attrs={"type": "date"}),
            "date_to": forms.DateInput(attrs={"type": "date"}),
        }


class ZKTecoDeviceForm(forms.ModelForm):
    class Meta:
        model = ZKTecoDevice
        fields = ["name", "ip_address", "port", "password", "location", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Main Entrance Device"}),
            "ip_address": forms.TextInput(attrs={"placeholder": "e.g. 192.168.1.100"}),
            "port": forms.NumberInput(attrs={"placeholder": "4370"}),
            "password": forms.NumberInput(attrs={"placeholder": "0"}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Head Office"}),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["receiver", "content", "is_announcement"]


class EmployeeCompleteForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = "__all__"
        exclude = [
            "password",
            "last_login",
            "is_superuser",
            "is_staff",
            "is_active",
            "user_permissions",
            "groups",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "passport_expiry": forms.DateInput(attrs={"type": "date"}),
            "hiring_date": forms.DateInput(attrs={"type": "date"}),
            "contract_start": forms.DateInput(attrs={"type": "date"}),
            "contract_end": forms.DateInput(attrs={"type": "date"}),
            "iqama_expiry_date": forms.DateInput(attrs={"type": "date"}),
            "work_start_time": forms.TimeInput(attrs={"type": "time"}),
            "work_end_time": forms.TimeInput(attrs={"type": "time"}),
        }


from .models import AdvanceSalaryRequest


class AdvanceSalaryRequestForm(forms.ModelForm):
    class Meta:
        model = AdvanceSalaryRequest
        fields = ["amount", "reason", "repayment_month"]
        widgets = {
            "reason": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Reason for advance salary request"}
            ),
            "repayment_month": forms.TextInput(attrs={"placeholder": "e.g. May 2025"}),
            "amount": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
        }
