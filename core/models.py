from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.validators import RegexValidator
from django_countries.fields import CountryField
from django.utils import timezone


class EmployeeManager(BaseUserManager):
    def create_user(self, iqama_number, password=None, **extra_fields):
        if not iqama_number:
            raise ValueError("Iqama number is required")
        user = self.model(iqama_number=iqama_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, iqama_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "hr")  # Superuser is HR by default
        return self.create_user(iqama_number, password, **extra_fields)


class Department(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sub_departments",
    )

    def __str__(self):
        return self.name


class Employee(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("ceo", "CEO 👑"),
        ("hr", "HR ⭐ "),
        ("manager", "Manager"),
        ("branch_manager", "Branch Manager"),
        ("officer", "Officer"),
        ("employee", "Employee"),
    ]

    ADVANCE_ROLE_CHOICES = [
        ("top_manager", "Top Manager"),
        ("accountant", "Accountant"),
        ("sub_accountant", "Sub Accountant"),
        ("bank_user", "Bank User"),
    ]

    advance_role = models.CharField(
        max_length=20,
        choices=ADVANCE_ROLE_CHOICES,
        blank=True,
        default="",
    )

    iqama_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r"^\d+$", "Only numbers allowed")],
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    full_name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="employee")
    nationality = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    place_of_birth = models.CharField(max_length=100, blank=True)
    gender = models.CharField(
        max_length=10, choices=[("male", "Male"), ("female", "Female")], blank=True
    )
    marital_status = models.CharField(
        max_length=20,
        choices=[
            ("single", "Single"),
            ("married", "Married"),
            ("divorced", "Divorced"),
            ("widowed", "Widowed"),
        ],
        blank=True,
    )
    number_of_dependents = models.IntegerField(default=0)
    religion = models.CharField(
        max_length=50,
        choices=[
            ("islam", "Islam"),
            ("christianity", "Christianity"),
            ("hinduism", "Hinduism"),
            ("buddhism", "Buddhism"),
            ("sikhism", "Sikhism"),
            ("judaism", "Judaism"),
            ("other", "Other"),
        ],
        blank=True,
    )
    personal_photo = models.ImageField(upload_to="photos/", null=True, blank=True)
    passport_number = models.CharField(max_length=50, blank=True)
    passport_expiry = models.DateField(null=True, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    alt_mobile_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    current_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = CountryField(default="SA", blank=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_relationship = models.CharField(
        max_length=100,
        choices=[
            ("spouse", "Spouse"),
            ("parent", "Parent"),
            ("child", "Child"),
            ("sibling", "Sibling"),
            ("friend", "Friend"),
            ("other", "Other"),
        ],
        blank=True,
    )
    emergency_contact_number = models.CharField(max_length=20, blank=True)
    social_insurance_number = models.CharField(max_length=50, blank=True)
    bank_account_iban = models.CharField(max_length=50, blank=True)
    bank_name = models.CharField(
        max_length=50,
        choices=[
            ("alrajhi", "Al Rajhi Bank"),
            ("alinma", "Alinma Bank"),
            ("riyad", "Riyad Bank"),
            ("snb", "Saudi National Bank (SNB)"),
            ("sabb", "SABB (Saudi British Bank)"),
            ("albilad", "Bank Albilad"),
            ("aljazira", "Bank Aljazira"),
            ("arab_national", "Arab National Bank"),
            ("gulf_international", "Gulf International Bank"),
            ("saudi_investment", "The Saudi Investment Bank"),
            ("emirates_nbd", "Emirates NBD"),
            ("bank_muscat", "Bank Muscat"),
            ("other", "Other"),
        ],
        blank=True,
    )
    iqama_expiry_date = models.DateField(null=True, blank=True)
    profession_per_iqama = models.CharField(max_length=200, blank=True)
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    zkteco_uid = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Numeric User ID assigned by the ZKTeco device (shown in device logs)",
    )
    job_title = models.CharField(max_length=200, blank=True)
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL
    )
    branch = models.CharField(max_length=200, blank=True)
    hiring_date = models.DateField(null=True, blank=True)
    contract_type = models.CharField(
        max_length=20,
        choices=[
            ("full_time", "Full-time"),
            ("part_time", "Part-time"),
            ("temporary", "Temporary"),
        ],
        blank=True,
    )
    contract_duration = models.CharField(max_length=100, blank=True)
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    probation_period = models.IntegerField(default=90)
    direct_manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subordinates",
    )
    work_location = models.CharField(
        max_length=20,
        choices=[
            ("office", "Office"),
            ("branch", "Branch"),
            ("warehouse", "Warehouse"),
        ],
        blank=True,
    )
    employment_status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("terminated", "Terminated"),
        ],
        default="active",
    )
    reason_for_termination = models.TextField(blank=True)
    working_days = models.CharField(max_length=200, blank=True)
    working_hours = models.DecimalField(max_digits=4, decimal_places=1, default=8)
    work_system = models.CharField(
        max_length=20,
        choices=[("fixed", "Fixed"), ("shifts", "Shifts")],
        default="fixed",
    )
    work_start_time = models.TimeField(null=True, blank=True)
    work_end_time = models.TimeField(null=True, blank=True)
    lunch_break_minutes = models.IntegerField(default=60)
    weekly_off_days = models.CharField(
        max_length=100, blank=True, default="Friday,Saturday"
    )
    job_description = models.TextField(blank=True)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    proficiency_allowance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    salary_payment_method = models.CharField(
        max_length=20,
        choices=[("bank", "Bank Transfer"), ("cash", "Cash")],
        default="bank",
    )
    salary_payment_date = models.IntegerField(default=1)

    objects = EmployeeManager()
    USERNAME_FIELD = "iqama_number"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.full_name

    @property
    def total_salary(self):
        return (
            self.basic_salary
            + self.housing_allowance
            + self.proficiency_allowance
            + self.other_allowances
        )

    @property
    def is_hr(self):
        return self.role == "hr" or self.is_superuser or self.is_staff


class TimeOffType(models.Model):
    name = models.CharField(max_length=100)
    days_allowed = models.IntegerField(default=0)
    color = models.CharField(max_length=20, default="#4f46e5")

    def __str__(self):
        return self.name


class TimeOffRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("refused", "Refused"),
        ("cancelled", "Cancelled"),
    ]

    APPROVAL_STATE_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("branch_approved", "Branch Manager Approved"),
        ("manager_approved", "Manager Approved"),
        ("ceo_approved", "CEO Approved"),
        ("hr_approved", "HR Approved"),
        ("approved", "Approved"),
        ("refused", "Refused"),
    ]

    REQUESTER_ROLE_CHOICES = [
        ("employee", "Employee"),
        ("officer", "Officer"),
        ("branch_manager", "Branch Manager"),
        ("manager", "Manager"),
        ("hr", "HR"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    approval_state = models.CharField(
        max_length=20, choices=APPROVAL_STATE_CHOICES, default="draft"
    )
    requester_role = models.CharField(
        max_length=20, choices=REQUESTER_ROLE_CHOICES, blank=True
    )
    refused_reason = models.TextField(blank=True)
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="time_off_requests"
    )
    leave_type = models.ForeignKey(TimeOffType, on_delete=models.CASCADE)
    date_from = models.DateField()
    date_to = models.DateField()
    supporting_document = models.FileField(
        upload_to="timeoff_documents/",
        null=True,
        blank=True,
    )
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    approved_by = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type.name}"

    @property
    def is_branch_manager(self):
        return self.role == "branch_manager"

    @property
    def is_manager(self):
        return self.role == "manager"

    @property
    def is_ceo(self):
        return self.role == "ceo"

    @property
    def days_count(self):
        return (self.date_to - self.date_from).days + 1


class AttendanceRecord(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="attendance"
    )
    date = models.DateField()
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    source = models.CharField(
        max_length=20,
        choices=[("zkteco", "ZKTeco"), ("manual", "Manual")],
        default="zkteco",
    )

    class Meta:
        unique_together = ("employee", "date")

    @property
    def worked_hours(self):
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            return round(delta.seconds / 3600, 2)
        return 0


class ZKTecoDevice(models.Model):
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField(default=4370)
    password = models.IntegerField(default=0)  # ADD THIS
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    device_name = models.CharField(max_length=200, blank=True, editable=False)
    device_firmware = models.CharField(max_length=100, blank=True, editable=False)
    device_serial_no = models.CharField(max_length=100, blank=True, editable=False)
    device_platform = models.CharField(max_length=100, blank=True, editable=False)
    device_mac = models.CharField(max_length=50, blank=True, editable=False)
    connection_status = models.BooleanField(default=False, editable=False)

    def __str__(self):
        return f"{self.name} ({self.ip_address}:{self.port})"


class ZKAttendanceLog(models.Model):
    device = models.ForeignKey(
        ZKTecoDevice, on_delete=models.CASCADE, related_name="logs"
    )
    user_id = models.CharField(max_length=50)
    employee_name = models.CharField(max_length=200, blank=True)
    punch_time = models.DateTimeField()
    punch_type = models.CharField(max_length=20, blank=True)
    status = models.IntegerField(default=0)

    class Meta:
        ordering = ["-punch_time"]

    def __str__(self):
        return f"{self.employee_name or self.user_id} - {self.punch_time}"


class Message(models.Model):
    sender = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="received_messages",
    )
    content = models.TextField()
    attachment = models.FileField(
        upload_to="chat_attachments/",
        null=True,
        blank=True,
    )
    is_announcement = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)


class Asset(models.Model):
    CUSTODY_TYPE_CHOICES = [
        ("office_equipment", "Office Equipment Custody"),
        ("vehicle", "Vehicle Custody"),
        ("it_equipment", "IT / Technical Equipment Custody"),
        ("cash", "Cash Custody"),
        ("documents", "Documents / Records Custody"),
        ("tools", "Tools / Equipment Custody"),
        ("other", "Special / Other Custody"),
    ]
    is_returned = models.BooleanField(default=False)
    condition_on_handover = models.TextField(blank=True)
    condition_on_return = models.TextField(blank=True)

    name = models.CharField(max_length=200)
    custody_type = models.CharField(max_length=50, choices=CUSTODY_TYPE_CHOICES)
    description = models.TextField(blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)

    assigned_to = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handover_assets",
    )
    assigned_date = models.DateField(null=True, blank=True)
    expected_return_date = models.DateField(null=True, blank=True)
    returned_date = models.DateField(null=True, blank=True)
    is_returned = models.BooleanField(default=False)
    condition_on_handover = models.TextField(
        blank=True, help_text="Condition when handed over"
    )
    condition_on_return = models.TextField(
        blank=True, help_text="Condition when returned"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "Employee", on_delete=models.SET_NULL, null=True, related_name="created_assets"
    )

    def __str__(self):
        return f"{self.name} ({self.get_custody_type_display()})"

    @property
    def status(self):
        if self.is_returned:
            return "returned"
        elif self.assigned_to:
            return "handed_over"
        else:
            return "available"


class EmployeeDocument(models.Model):
    DOCUMENT_TYPES = [
        ("iqama", "Iqama / ID"),
        ("passport", "Passport"),
        ("visa", "Visa"),
        ("driving_license", "Driving License"),
        ("education_certificate", "Education Certificate"),
        ("experience_letter", "Experience Letter"),
        ("contract", "Contract"),
        ("insurance", "Insurance"),
        ("other", "Other"),
    ]
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    document_file = models.FileField(
        upload_to="employee_documents/", null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_documents",
    )

    def __str__(self):
        return f"{self.employee.full_name} - {self.get_document_type_display()}"

    @property
    def is_expired(self):
        from django.utils import timezone

        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def days_until_expiry(self):
        from django.utils import timezone

        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None


class AdvanceSalaryRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("paid", "Paid"),
    ]
    ADVANCE_APPROVAL_STATE_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("hr_approved", "HR Approved"),
        ("accountant_approved", "Accountant Approved"),
        ("sub_accountant_approved", "Sub Accountant Approved"),
        ("ceo_approved", "CEO Approved"),
        ("bank_approved", "Bank Approved"),
        ("paid", "Paid"),
        ("rejected", "Rejected"),
    ]
    ADVANCE_REQUESTER_ROLE_CHOICES = [
        ("top_manager", "Top Manager"),
        ("hr", "HR"),
        ("other", "Other"),
    ]
    approval_state = models.CharField(
        max_length=30,
        choices=ADVANCE_APPROVAL_STATE_CHOICES,
        default="draft",
    )
    requester_role = models.CharField(
        max_length=20,
        choices=ADVANCE_REQUESTER_ROLE_CHOICES,
        blank=True,
        default="",
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="advance_requests"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True)
    requested_date = models.DateField(auto_now_add=True)
    repayment_month = models.CharField(
        max_length=20, blank=True, help_text="e.g. May 2025"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_advances",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    hr_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.full_name} - {self.amount} SAR ({self.status})"

    class Meta:
        ordering = ["-created_at"]
