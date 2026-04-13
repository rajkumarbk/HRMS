from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import (
    Employee,
    TimeOffRequest,
    AttendanceRecord,
    ZKTecoDevice,
    Message,
    Department,
    TimeOffType,
    Asset,
    AdvanceSalaryRequest,
)
from .forms import (
    LoginForm,
    EmployeeBasicForm,
    EmployeeContactForm,
    EmployeeWorkForm,
    EmployeeFinancialForm,
    TimeOffRequestForm,
    ZKTecoDeviceForm,
    MessageForm,
    AdvanceSalaryRequestForm,
)
from .decorators import hr_required, employee_owner_or_hr_required
from django.core.mail import send_mail
from django.conf import settings
from .models import EmployeeDocument
from .forms import EmployeeDocumentForm

import logging
import csv
from django.core.paginator import Paginator
from django.http import HttpResponse

logger = logging.getLogger(__name__)

try:
    from zk import ZK  # type: ignore
except ImportError:
    ZK = None


def _connect_device(ip, port, password=0):
    if ZK is None:
        return None, None
    try:
        zk = ZK(
            ip,
            port=port,
            timeout=10,
            password=password,
            force_udp=False,
            ommit_ping=False,
        )
        conn = zk.connect()
        return conn, zk
    except Exception as e:
        logger.warning(f"ZKTeco connection failed: {e}")
        return None, None


def _process_zk_logs_to_attendance(device):
    from .models import ZKAttendanceLog
    from collections import defaultdict

    employee_cache = {}
    logs = device.logs.order_by("punch_time")
    touched = 0
    skipped_uids = set()

    grouped = defaultdict(list)
    for log in logs:
        date = timezone.localtime(log.punch_time).date()
        grouped[(log.user_id, date)].append(log)

    for (user_id, date), day_logs in grouped.items():
        if user_id not in employee_cache:
            emp = None

            # Strategy 1: match ZKTeco user_id → Employee.zkteco_uid
            try:
                emp = Employee.objects.get(zkteco_uid=user_id)
            except Employee.DoesNotExist:
                pass

            # Strategy 2: match ZKTeco user_id → Employee.employee_id (exact)
            if emp is None:
                try:
                    emp = Employee.objects.get(employee_id=user_id)
                except Employee.DoesNotExist:
                    pass

            # Strategy 3: match by name (case-insensitive)
            if emp is None:
                name = next(
                    (l.employee_name for l in day_logs if l.employee_name), None
                )
                if name:
                    try:
                        emp = Employee.objects.get(full_name__iexact=name.strip())
                    except (Employee.DoesNotExist, Employee.MultipleObjectsReturned):
                        pass

            if emp is None:
                skipped_uids.add(user_id)

            employee_cache[user_id] = emp

        employee = employee_cache[user_id]
        if employee is None:
            continue

        check_ins = [l.punch_time for l in day_logs if l.punch_type == "0"]
        check_outs = [l.punch_time for l in day_logs if l.punch_type == "1"]
        check_in = min(check_ins) if check_ins else None
        check_out = max(check_outs) if check_outs else None

        # If device doesn't differentiate punch types, use first as in, last as out
        if check_in is None and check_out is None:
            all_times = sorted([l.punch_time for l in day_logs])
            check_in = all_times[0]
            check_out = all_times[-1] if len(all_times) > 1 else None

        AttendanceRecord.objects.update_or_create(
            employee=employee,
            date=date,
            defaults={
                "check_in": check_in,
                "check_out": check_out,
                "source": "zkteco",
            },
        )
        touched += 1

    if skipped_uids:
        logger.warning(
            f"ZKTeco sync: could not match these device UIDs to any employee: {skipped_uids}. "
            f"Set the 'zkteco_uid' field on the Employee record to fix this."
        )

    return touched


@login_required
@hr_required
def device_add(request):
    form = ZKTecoDeviceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if ZK is None:
            messages.error(request, "pyzk not installed. Run: pip install pyzk")
            return render(request, "attendance/device_form.html", {"form": form})

        device = form.save(commit=False)
        conn, zk = _connect_device(device.ip_address, device.port, device.password)
        if not conn:
            messages.error(
                request,
                f"Could not connect to {device.ip_address}:{device.port}. Check IP, port and network.",
            )
            return render(request, "attendance/device_form.html", {"form": form})

        try:
            device.device_name = conn.get_device_name() or ""
            device.device_firmware = conn.get_firmware_version() or ""
            device.device_serial_no = conn.get_serialnumber() or ""
            device.device_platform = conn.get_platform() or ""
            device.device_mac = conn.get_mac() or ""
            device.connection_status = True
            device.last_sync = timezone.now()
        except Exception as e:
            logger.warning(f"Could not fetch device info: {e}")
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass

        device.save()
        messages.success(
            request, f'Device "{device.name}" connected and added successfully.'
        )
        return redirect("device_detail", pk=device.pk)

    return render(request, "attendance/device_form.html", {"form": form})


@login_required
@hr_required
def device_detail(request, pk):
    from .models import ZKAttendanceLog

    device = get_object_or_404(ZKTecoDevice, pk=pk)

    if request.GET.get("refresh"):
        if ZK is None:
            messages.error(request, "pyzk not installed. Run: pip install pyzk")
        else:
            conn, zk = _connect_device(device.ip_address, device.port, device.password)
            if conn:
                try:
                    device.device_name = conn.get_device_name() or ""
                    device.device_firmware = conn.get_firmware_version() or ""
                    device.device_serial_no = conn.get_serialnumber() or ""
                    device.device_platform = conn.get_platform() or ""
                    device.device_mac = conn.get_mac() or ""
                    device.connection_status = True
                    device.last_sync = timezone.now()
                    device.save()
                    messages.success(request, "Device info refreshed.")
                except Exception as e:
                    messages.warning(
                        request, f"Connected but could not fetch info: {e}"
                    )
                finally:
                    try:
                        conn.disconnect()
                    except Exception:
                        pass
            else:
                device.connection_status = False
                device.save()
                messages.error(request, "Could not reach device.")

    logs_qs = device.logs.all()
    search_name = request.GET.get("name", "").strip()
    search_date_from = request.GET.get("date_from", "").strip()
    search_date_to = request.GET.get("date_to", "").strip()

    if search_name:
        logs_qs = logs_qs.filter(employee_name__icontains=search_name)
    if search_date_from:
        logs_qs = logs_qs.filter(punch_time__date__gte=search_date_from)
    if search_date_to:
        logs_qs = logs_qs.filter(punch_time__date__lte=search_date_to)

    paginator = Paginator(logs_qs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "attendance/device_detail.html",
        {
            "device": device,
            "page_obj": page_obj,
            "search_name": search_name,
            "search_date_from": search_date_from,
            "search_date_to": search_date_to,
            "total_logs": logs_qs.count(),
        },
    )


@login_required
@hr_required
def device_sync(request, pk):
    from .models import ZKAttendanceLog

    device = get_object_or_404(ZKTecoDevice, pk=pk)

    if ZK is None:
        messages.error(request, "pyzk not installed. Run: pip install pyzk")
        return redirect("device_detail", pk=pk)

    conn, zk = _connect_device(device.ip_address, device.port, device.password)
    if not conn:
        messages.error(
            request, f"Could not connect to {device.ip_address}:{device.port}."
        )
        return redirect("device_detail", pk=pk)

    try:
        conn.disable_device()

        user_map = {}  # zk_user_id -> name
        try:
            for u in conn.get_users():
                user_map[str(u.user_id)] = u.name
        except Exception as e:
            logger.warning(f"Could not fetch users: {e}")

        attendances = conn.get_attendance()
        conn.enable_device()

        synced = 0
        for att in attendances:
            uid = str(att.user_id)
            _, created = ZKAttendanceLog.objects.get_or_create(
                device=device,
                user_id=uid,
                punch_time=att.timestamp,
                defaults={
                    "employee_name": user_map.get(uid, ""),
                    "punch_type": str(att.punch),
                    "status": att.status,
                },
            )
            if created:
                synced += 1

        device.last_sync = timezone.now()
        device.connection_status = True
        device.save()

        # Convert raw logs → AttendanceRecord rows
        linked = _process_zk_logs_to_attendance(device)

        messages.success(
            request,
            f"Sync complete. {synced} new punch records pulled, {linked} attendance records updated.",
        )
    except Exception as e:
        messages.error(request, f"Sync failed: {e}")
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass

    return redirect("device_detail", pk=pk)


@login_required
@hr_required
def attendance_report_csv(request, pk):
    from .models import ZKAttendanceLog

    device = get_object_or_404(ZKTecoDevice, pk=pk)

    logs_qs = device.logs.all()
    search_name = request.GET.get("name", "").strip()
    search_date_from = request.GET.get("date_from", "").strip()
    search_date_to = request.GET.get("date_to", "").strip()

    if search_name:
        logs_qs = logs_qs.filter(employee_name__icontains=search_name)
    if search_date_from:
        logs_qs = logs_qs.filter(punch_time__date__gte=search_date_from)
    if search_date_to:
        logs_qs = logs_qs.filter(punch_time__date__lte=search_date_to)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="attendance_{device.name}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(["User ID", "Employee Name", "Punch Time", "Punch Type", "Status"])

    punch_type_map = {
        "0": "Check In",
        "1": "Check Out",
        "2": "Break Out",
        "3": "Break In",
        "4": "Overtime In",
        "5": "Overtime Out",
    }
    for log in logs_qs:
        writer.writerow(
            [
                log.user_id,
                log.employee_name or "—",
                log.punch_time.strftime("%Y-%m-%d %H:%M:%S"),
                punch_type_map.get(log.punch_type, log.punch_type),
                log.status,
            ]
        )
    return response


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm()
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            login(request, form.cleaned_data["user"])
            return redirect(request.GET.get("next", "dashboard"))
    return render(request, "auth/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    if request.user.is_hr:
        # HR Dashboard
        total_employees = Employee.objects.filter(employment_status="active").count()
        pending_leaves = TimeOffRequest.objects.filter(status="pending").count()
        today = timezone.now().date()
        present_today = AttendanceRecord.objects.filter(date=today).count()
        unread_messages = Message.objects.filter(
            receiver=request.user, is_read=False
        ).count()
        recent_employees = Employee.objects.filter(employment_status="active").order_by(
            "-date_joined"
        )[:5]
        recent_leaves = TimeOffRequest.objects.order_by("-created_at")[:5]

        context = {
            "total_employees": total_employees,
            "pending_leaves": pending_leaves,
            "present_today": present_today,
            "unread_messages": unread_messages,
            "recent_employees": recent_employees,
            "recent_leaves": recent_leaves,
            "is_hr_dashboard": True,
        }
        return render(request, "dashboard.html", context)

    else:
        # Regular Employee Dashboard
        employee = request.user
        today = timezone.now().date()

        # Attendance stats
        attendance_today = AttendanceRecord.objects.filter(
            employee=employee, date=today
        ).first()
        # Attendance period: 21st of previous month to 20th of current month
        if today.day >= 21:
            period_start = today.replace(day=21)
            period_end = today
        else:
            # We're in 1-20, so period started on 21st of previous month
            first_of_month = today.replace(day=1)
            prev_month = first_of_month - timezone.timedelta(days=1)
            period_start = prev_month.replace(day=21)
            period_end = today

        attendance_this_month = AttendanceRecord.objects.filter(
            employee=employee,
            date__gte=period_start,
            date__lte=period_end,
        ).count()

        # Time off stats
        pending_leaves = TimeOffRequest.objects.filter(
            employee=employee, status="pending"
        ).count()
        approved_leaves = TimeOffRequest.objects.filter(
            employee=employee, status="approved"
        ).count()
        total_leaves_taken = TimeOffRequest.objects.filter(
            employee=employee, status="approved"
        ).count()

        # Recent time off requests
        recent_leave_requests = TimeOffRequest.objects.filter(
            employee=employee
        ).order_by("-created_at")[:5]

        # Recent attendance
        recent_attendance = AttendanceRecord.objects.filter(employee=employee).order_by(
            "-date"
        )[:10]

        # Unread messages
        unread_messages = Message.objects.filter(
            receiver=employee, is_read=False
        ).count()
        advance_pending = AdvanceSalaryRequest.objects.filter(
            employee=employee, status="pending"
        ).count()
        context = {
            "is_employee_dashboard": True,
            "employee": employee,
            "attendance_today": attendance_today,
            "attendance_this_month": attendance_this_month,
            "pending_leaves": pending_leaves,
            "approved_leaves": approved_leaves,
            "total_leaves_taken": total_leaves_taken,
            "recent_leave_requests": recent_leave_requests,
            "recent_attendance": recent_attendance,
            "unread_messages": unread_messages,
            "advance_pending": advance_pending,
            "today": today,
        }
        return render(request, "employee_dashboard.html", context)


@login_required
@hr_required
def employee_list(request):
    employees = Employee.objects.all()
    q = request.GET.get("q", "")
    if q:
        employees = employees.filter(
            Q(full_name__icontains=q)
            | Q(iqama_number__icontains=q)
            | Q(job_title__icontains=q)
        )
    dept = request.GET.get("dept", "")
    if dept:
        employees = employees.filter(department_id=dept)
    departments = Department.objects.all()
    return render(
        request,
        "employee/list.html",
        {
            "employees": employees,
            "departments": departments,
            "q": q,
            "selected_dept": dept,
        },
    )


@login_required
@hr_required
def employee_create(request):
    departments = Department.objects.all()
    managers = Employee.objects.filter(is_active=True)

    if request.method == "POST":
        tab = request.POST.get("tab", "basic")

        # Create new employee instance
        employee = Employee()

        # Basic Info
        employee.full_name = request.POST.get("full_name")
        employee.iqama_number = request.POST.get("iqama_number")
        employee.nationality = request.POST.get("nationality", "")
        employee.date_of_birth = request.POST.get("date_of_birth") or None
        employee.place_of_birth = request.POST.get("place_of_birth", "")
        employee.gender = request.POST.get("gender", "")
        employee.marital_status = request.POST.get("marital_status", "")
        employee.number_of_dependents = int(request.POST.get("number_of_dependents", 0))
        employee.passport_number = request.POST.get("passport_number", "")
        employee.passport_expiry = request.POST.get("passport_expiry") or None
        # employee.zkteco_uid = request.POST.get("zkteco_uid", "") or None
        employee.zkteco_uid = request.POST.get("zkteco_uid", "").strip() or None
        if request.FILES.get("personal_photo"):
            employee.personal_photo = request.FILES["personal_photo"]

        # Contact Info
        employee.mobile_number = request.POST.get("mobile_number", "")
        employee.alt_mobile_number = request.POST.get("alt_mobile_number", "")
        employee.email = request.POST.get("email", "")
        employee.current_address = request.POST.get("current_address", "")
        employee.city = request.POST.get("city", "")
        employee.country = request.POST.get(
            "country", "SA"
        )  # 'SA' is the code for Saudi Arabia
        employee.emergency_contact_name = request.POST.get("emergency_contact_name", "")
        employee.emergency_relationship = request.POST.get("emergency_relationship", "")
        employee.emergency_contact_number = request.POST.get(
            "emergency_contact_number", ""
        )

        # Work Info
        employee.employee_id = request.POST.get("employee_id", "").strip() or None
        employee.job_title = request.POST.get("job_title", "")
        employee.branch = request.POST.get("branch", "")
        employee.hiring_date = request.POST.get("hiring_date") or None
        employee.contract_type = request.POST.get("contract_type", "")
        employee.contract_duration = request.POST.get("contract_duration", "")
        employee.contract_start = request.POST.get("contract_start") or None
        employee.contract_end = request.POST.get("contract_end") or None
        employee.probation_period = int(request.POST.get("probation_period", 90))
        employee.work_location = request.POST.get("work_location", "")
        employee.employment_status = request.POST.get("employment_status", "active")
        employee.reason_for_termination = request.POST.get("reason_for_termination", "")
        employee.working_days = request.POST.get("working_days", "Sunday-Thursday")
        employee.working_hours = float(request.POST.get("working_hours", 8))
        employee.work_system = request.POST.get("work_system", "fixed")
        employee.work_start_time = request.POST.get("work_start_time") or None
        employee.work_end_time = request.POST.get("work_end_time") or None
        employee.lunch_break_minutes = int(request.POST.get("lunch_break_minutes", 60))
        employee.weekly_off_days = request.POST.get(
            "weekly_off_days", "Friday,Saturday"
        )
        employee.job_description = request.POST.get("job_description", "")

        # Department & Manager
        dept_id = request.POST.get("department")
        if dept_id:
            employee.department_id = int(dept_id)
        manager_id = request.POST.get("direct_manager")
        if manager_id:
            employee.direct_manager_id = int(manager_id)

        # Financial Info
        employee.social_insurance_number = request.POST.get(
            "social_insurance_number", ""
        )
        employee.bank_account_iban = request.POST.get("bank_account_iban", "")
        employee.bank_name = request.POST.get("bank_name", "")
        employee.iqama_expiry_date = request.POST.get("iqama_expiry_date") or None
        employee.profession_per_iqama = request.POST.get("profession_per_iqama", "")
        employee.basic_salary = float(request.POST.get("basic_salary", 0))
        employee.housing_allowance = float(request.POST.get("housing_allowance", 0))
        employee.proficiency_allowance = float(
            request.POST.get("proficiency_allowance", 0)
        )
        employee.other_allowances = float(request.POST.get("other_allowances", 0))
        employee.salary_payment_method = request.POST.get(
            "salary_payment_method", "bank"
        )
        employee.salary_payment_date = int(request.POST.get("salary_payment_date", 1))

        # Set default password
        employee.set_password("12345678")

        # Validate required fields
        if not employee.full_name or not employee.iqama_number:
            messages.error(request, "Full name and Iqama number are required.")
            return render(
                request,
                "employee/create.html",
                {"departments": departments, "managers": managers, "active_tab": tab},
            )

        employee.save()

        doc_map = {
            "doc_iqama": "iqama",
            "doc_passport": "passport",
            "doc_contract": "contract",
            "doc_cv": "experience_letter",
            "doc_medical": "other",
            "doc_other": "other",
        }
        for field_name, doc_type in doc_map.items():
            file = request.FILES.get(field_name)
            if file:
                EmployeeDocument.objects.create(
                    employee=employee,
                    document_type=doc_type,
                    document_file=file,
                    uploaded_by=request.user,
                )

        messages.success(
            request, f"Employee {employee.full_name} created successfully."
        )
        return redirect("employee_detail", pk=employee.pk)

    # GET request
    return render(
        request,
        "employee/create.html",
        {
            "departments": departments,
            "managers": managers,
            "active_tab": request.GET.get("tab", "basic"),
        },
    )


@login_required
@employee_owner_or_hr_required  # HR or employee owner only
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    # Check if regular employee trying to access HR data sections
    is_hr_view = request.user.is_hr

    tab = request.GET.get("tab", "basic")
    forms_map = {
        "basic": EmployeeBasicForm(instance=employee),
        "contact": EmployeeContactForm(instance=employee),
        "work": EmployeeWorkForm(instance=employee),
        "financial": EmployeeFinancialForm(instance=employee),
        "documents": None,  # For uploading new documents
    }

    # For regular employees, only show basic and contact tabs (hide work and financial)
    allowed_tabs_for_employee = []

    if request.method == "POST":
        tab = request.POST.get("tab", "basic")

        # Check if regular employee is trying to edit restricted tabs
        if not request.user.is_hr and tab not in allowed_tabs_for_employee:
            messages.error(
                request,
                "You cannot edit these information. Please contact HR Manager for any updates.",
            )
            return redirect(f"/employees/{pk}/?tab=basic")

        if tab == "documents":
            # Documents tab doesn't use a form, just redirect back
            messages.success(request, "Document uploaded successfully.")
            return redirect(f"/employees/{pk}/?tab=documents")
        else:
            form_classes = {
                "basic": EmployeeBasicForm,
                "contact": EmployeeContactForm,
                "work": EmployeeWorkForm,
                "financial": EmployeeFinancialForm,
            }
            form = form_classes[tab](request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Information updated successfully.")
            return redirect(f"/employees/{pk}/?tab={tab}")
        forms_map[tab] = form

    context = {
        "employee": employee,
        "forms": forms_map,
        "active_tab": tab,
        "is_hr_view": is_hr_view,
        "allowed_tabs_for_employee": (
            allowed_tabs_for_employee if not request.user.is_hr else None
        ),
    }
    return render(request, "employee/detail.html", context)


# --- TIME OFF VIEWS ---

def _get_requester_role(user):
    """Mirrors Odoo's _get_requester_role — highest role wins."""
    role = user.role
    if role in ("hr",):
        return "hr"
    if role in ("manager",):
        return "manager"
    if role in ("branch_manager",):
        return "branch_manager"
    if role in ("officer",):
        return "officer"
    return "employee"


def _is_respective_manager(user, leave_request):
    """Current user is the direct_manager of the leave requester."""
    return (
        leave_request.employee.direct_manager is not None
        and leave_request.employee.direct_manager == user
    )


def _can_approve(user, leave):
    """
    Returns the action name if the user can approve this leave at its current stage,
    otherwise None.

    Approval matrix (mirrors hr_leave.py):
      Branch Manager  → submitted        + requester=employee
      Manager         → branch_approved  + requester=employee
                        submitted        + requester=branch_manager
                        submitted        + requester=officer  (respective manager only)
      CEO             → submitted        + requester in (manager, hr)
      HR              → manager_approved OR ceo_approved (any requester)
    """
    state = leave.approval_state
    role = user.role

    if role == "hr":
        return state in ("manager_approved", "ceo_approved")
    if role == "ceo":
        return state == "submitted" and leave.requester_role in ("manager", "hr")
    if role == "manager":
        if leave.requester_role == "employee":
            return state == "branch_approved"
        if leave.requester_role == "branch_manager":
            return state == "submitted"
        if leave.requester_role == "officer":
            return state == "submitted" and _is_respective_manager(user, leave)
        return False
    if role == "branch_manager":
        return state == "submitted" and leave.requester_role == "employee"
    return False


def _can_refuse(user, leave):
    """Refuse mirrors approve — same stage gate. HR can refuse any pending stage."""
    state = leave.approval_state
    if state in ("draft", "approved", "refused"):
        return False
    role = user.role
    if role == "hr":
        return state in ("manager_approved", "ceo_approved")
    if role == "ceo":
        return state == "submitted" and leave.requester_role in ("manager", "hr")
    if role == "manager":
        if leave.requester_role == "employee":
            return state == "branch_approved"
        if leave.requester_role == "branch_manager":
            return state == "submitted"
        if leave.requester_role == "officer":
            return state == "submitted" and _is_respective_manager(user, leave)
        return False
    if role == "branch_manager":
        return state == "submitted" and leave.requester_role == "employee"
    return False


@login_required
def timeoff_list(request):
    user = request.user
    role = user.role

    if role == "hr":
        # HR sees everything
        requests_qs = TimeOffRequest.objects.all().select_related(
            "employee", "leave_type"
        ).order_by("-created_at")

    elif role == "branch_manager":
        # Only sees: submitted employee requests (their turn to approve)
        # + their own requests
        requests_qs = TimeOffRequest.objects.filter(
            Q(employee=user) |
            Q(approval_state="submitted", requester_role="employee")
        ).select_related("employee", "leave_type").order_by("-created_at").distinct()

    elif role == "manager":
        # Sees:
        #   - own requests
        #   - employee requests at branch_approved (their turn)
        #   - branch_manager requests at submitted (their turn)
        #   - officer requests at submitted where they are the direct_manager
        requests_qs = TimeOffRequest.objects.filter(
            Q(employee=user) |
            Q(approval_state="branch_approved", requester_role="employee") |
            Q(approval_state="submitted", requester_role="branch_manager") |
            Q(approval_state="submitted", requester_role="officer", employee__direct_manager=user)
        ).select_related("employee", "leave_type").order_by("-created_at").distinct()

    elif role == "ceo":
        # Only sees: manager/hr requests at submitted (their turn)
        # + their own requests
        requests_qs = TimeOffRequest.objects.filter(
            Q(employee=user) |
            Q(approval_state="submitted", requester_role__in=["manager", "hr"])
        ).select_related("employee", "leave_type").order_by("-created_at").distinct()

    else:
        # Regular employee / officer — only their own requests
        requests_qs = TimeOffRequest.objects.filter(
            employee=user
        ).select_related("leave_type").order_by("-created_at")

    # Annotate approve/refuse flags
    for req in requests_qs:
        req.user_can_approve = _can_approve(user, req)
        req.user_can_refuse = _can_refuse(user, req)

    leave_types = TimeOffType.objects.all()
    pending_count = requests_qs.filter(
        approval_state__in=["submitted", "branch_approved", "manager_approved", "ceo_approved"]
    ).count()

    return render(request, "timeoff/list.html", {
        "requests": requests_qs,
        "leave_types": leave_types,
        # "pending_count": pending_count,
        "user_role": role,
    })


@login_required
def timeoff_create(request):
    form = TimeOffRequestForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.employee = request.user
        obj.requester_role = _get_requester_role(request.user)
        obj.approval_state = "submitted"
        obj.status = "pending"
        if request.FILES.get("supporting_document"):
            obj.supporting_document = request.FILES["supporting_document"]
        obj.save()
        messages.success(request, "Leave request submitted successfully.")
        return redirect("timeoff_list")
    return render(request, "timeoff/create.html", {"form": form})


@login_required
def timeoff_approve(request, pk):
    """
    Single approval endpoint — advances the leave through its stage-specific flow.
    The next state is determined by requester_role + current approval_state.
    """
    leave = get_object_or_404(TimeOffRequest, pk=pk)
    user = request.user

    if not _can_approve(user, leave):
        messages.error(request, "You are not authorised to approve this request at its current stage.")
        return redirect("timeoff_list")

    role = user.role
    state = leave.approval_state
    rr = leave.requester_role  # requester_role

    # Determine next state
    if role == "branch_manager":
        # Employee flow: submitted → branch_approved
        leave.approval_state = "branch_approved"
        messages.success(request, "Leave approved by Branch Manager. Forwarded to Manager.")

    elif role == "manager":
        # All manager flows land on manager_approved → then HR
        leave.approval_state = "manager_approved"
        messages.success(request, "Leave approved by Manager. Forwarded to HR.")

    elif role == "ceo":
        # Manager/HR requester flow: submitted → ceo_approved
        leave.approval_state = "ceo_approved"
        messages.success(request, "Leave approved by CEO. Forwarded to HR.")

    elif role == "hr":
        # Final approval
        leave.approval_state = "approved"
        leave.status = "approved"
        leave.approved_by = user
        messages.success(request, "Leave fully approved.")

    leave.save()
    return redirect("timeoff_list")


@login_required
def timeoff_refuse(request, pk):
    leave = get_object_or_404(TimeOffRequest, pk=pk)
    user = request.user

    if not _can_refuse(user, leave):
        messages.error(request, "You are not authorised to refuse this request at its current stage.")
        return redirect("timeoff_list")

    reason = request.POST.get("reason", "").strip()
    leave.approval_state = "refused"
    leave.status = "refused"
    leave.refused_reason = reason
    leave.save()
    messages.success(request, "Leave request refused.")
    return redirect("timeoff_list")


@login_required
def timeoff_reset(request, pk):
    """Allow the employee (or HR) to reset a refused leave back to draft."""
    leave = get_object_or_404(TimeOffRequest, pk=pk)
    if leave.approval_state != "refused":
        messages.error(request, "Only refused leaves can be reset.")
        return redirect("timeoff_list")
    if leave.employee != request.user and not request.user.role == "hr":
        messages.error(request, "You can only reset your own leave requests.")
        return redirect("timeoff_list")
    leave.approval_state = "draft"
    leave.status = "pending"
    leave.requester_role = ""
    leave.refused_reason = ""
    leave.save()
    messages.success(request, "Leave request reset to draft. You may re-submit it.")
    return redirect("timeoff_list")


# --- ATTENDANCE VIEWS ---
@login_required
def attendance_list(request):
    today = timezone.now().date()

    if request.user.is_hr:
        # HR sees all attendance records
        devices = ZKTecoDevice.objects.all()
        records = (
            AttendanceRecord.objects.filter(date=today)
            .select_related("employee")
            .order_by("-check_in")
        )
    else:
        # Regular employee sees only their own attendance
        devices = None
        records = (
            AttendanceRecord.objects.filter(employee=request.user, date=today)
            .select_related("employee")
            .order_by("-check_in")
        )

    return render(
        request,
        "attendance/list.html",
        {"devices": devices, "records": records, "today": today},
    )


@login_required
@hr_required  # Only HR can sync attendance devices
def attendance_sync(request, device_id):
    device = get_object_or_404(ZKTecoDevice, pk=device_id)
    messages.info(
        request,
        f"Sync initiated for {device.name} ({device.ip_address}:{device.port}). Install pyzk library to enable real sync.",
    )
    return redirect("attendance_list")


@login_required
def my_attendance(request):
    employee = request.user
    qs = AttendanceRecord.objects.filter(employee=employee).order_by("-date")

    # Optional filters
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    # Month summary
    today = timezone.now().date()
    this_month_count = AttendanceRecord.objects.filter(
        employee=employee, date__year=today.year, date__month=today.month
    ).count()

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "attendance/my_attendance.html",
        {
            "page_obj": page_obj,
            "date_from": date_from,
            "date_to": date_to,
            "this_month_count": this_month_count,
            "employee": employee,
        },
    )


@login_required
@hr_required  # Only HR can add devices
def device_add(request):
    form = ZKTecoDeviceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Device added successfully.")
        return redirect("attendance_list")
    return render(request, "attendance/device_form.html", {"form": form})


# --- DISCUSS VIEWS ---
@login_required
def discuss(request):
    if request.user.is_hr:
        announcements = Message.objects.filter(is_announcement=True).order_by(
            "-created_at"
        )[:20]
        employees = Employee.objects.exclude(pk=request.user.pk).filter(is_active=True)
    else:
        # Regular employee sees announcements but only can chat with HR
        announcements = Message.objects.filter(is_announcement=True).order_by(
            "-created_at"
        )[:20]
        employees = Employee.objects.filter(role="hr", is_active=True).exclude(
            pk=request.user.pk
        )

    selected_user_id = request.GET.get("chat")
    chat_messages = []
    chat_user = None
    if selected_user_id:
        chat_user = get_object_or_404(Employee, pk=selected_user_id)
        chat_messages = Message.objects.filter(
            Q(sender=request.user, receiver=chat_user)
            | Q(sender=chat_user, receiver=request.user)
        ).order_by("created_at")
        Message.objects.filter(
            sender=chat_user, receiver=request.user, is_read=False
        ).update(is_read=True)

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        is_announce = request.POST.get("is_announcement") == "1"
        receiver_id = request.POST.get("receiver_id")

        # Only HR can make announcements
        if is_announce and not request.user.is_hr:
            messages.error(request, "Only HR can make announcements.")
            return redirect("discuss")

        if content:
            msg = Message(
                sender=request.user, content=content, is_announcement=is_announce
            )
            if not is_announce and receiver_id:
                msg.receiver_id = receiver_id
            if request.FILES.get("attachment"):
                msg.attachment = request.FILES["attachment"]
            msg.save()
            if is_announce:
                return redirect("discuss")
            return redirect(f"/discuss/?chat={receiver_id}")

    return render(
        request,
        "discuss/index.html",
        {
            "announcements": announcements,
            "employees": employees,
            "chat_messages": chat_messages,
            "chat_user": chat_user,
        },
    )

    # --- USER ACCOUNT VIEWS ---


@login_required
@hr_required
def user_accounts(request):
    employees = Employee.objects.all().order_by("-date_joined")
    # Get employees without accounts (those who can have accounts created)
    employees_without_account = Employee.objects.filter(is_active=True)

    return render(
        request,
        "user_accounts.html",
        {
            "employees": employees,
            "employees_without_account": employees_without_account,
        },
    )


@login_required
@hr_required
def create_user_account(request):
    if request.method == "POST":
        employee_id = request.POST.get("employee_id")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        role = request.POST.get("role")

        # Validation
        if not employee_id or not password or not role:
            messages.error(request, "All fields are required.")
            return redirect("user_accounts")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("user_accounts")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return redirect("user_accounts")

        try:
            employee = Employee.objects.get(pk=employee_id)

            # Check if employee already has an account (has password set)
            if employee.has_usable_password() and employee.password:
                messages.error(
                    request,
                    f"{employee.full_name} already has an account. You can reset their password instead.",
                )
                return redirect("user_accounts")

            employee.set_password(password)
            employee.role = role
            employee.is_active = True
            employee.save()

            messages.success(
                request,
                f"User account created for {employee.full_name} with role {role}.",
            )
        except Employee.DoesNotExist:
            messages.error(request, "Employee not found.")

        return redirect("user_accounts")

    return redirect("user_accounts")


@login_required
@hr_required
def reset_user_password(request):
    if request.method == "POST":
        employee_id = request.POST.get("employee_id")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not password or password != confirm_password:
            messages.error(request, "Passwords do not match or are empty.")
            return redirect("user_accounts")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return redirect("user_accounts")

        try:
            employee = Employee.objects.get(pk=employee_id)
            employee.set_password(password)
            employee.save()
            messages.success(request, f"Password reset for {employee.full_name}.")
        except Employee.DoesNotExist:
            messages.error(request, "Employee not found.")

        return redirect("user_accounts")

    return redirect("user_accounts")


@login_required
@hr_required
def toggle_user_status(request, pk):
    try:
        employee = Employee.objects.get(pk=pk)
        employee.is_active = not employee.is_active
        employee.save()
        status = "activated" if employee.is_active else "deactivated"
        messages.success(request, f"User account {status} for {employee.full_name}.")
    except Employee.DoesNotExist:
        messages.error(request, "Employee not found.")

    return redirect("user_accounts")


@login_required
@hr_required
def change_user_role(request, pk, role):
    if role not in ["ceo", "hr", "manager", "branch_manager", "officer", "employee"]:
        messages.error(request, "Invalid role.")
        return redirect("user_accounts")

    try:
        employee = Employee.objects.get(pk=pk)
        employee.role = role
        employee.save()
        messages.success(
            request, f"Role changed to {role.upper()} for {employee.full_name}."
        )
    except Employee.DoesNotExist:
        messages.error(request, "Employee not found.")

    return redirect("user_accounts")


# --- ASSET MANAGEMENT VIEWS ---
@login_required
def asset_handover_list(request):
    # Assets currently handed over (assigned AND NOT returned)
    handover_assets = Asset.objects.filter(
        is_returned=False, assigned_to__isnull=False
    ).order_by("-assigned_date")

    # Returned assets history (is_returned = True)
    returned_assets = Asset.objects.filter(is_returned=True).order_by("-returned_date")

    employees = Employee.objects.filter(is_active=True)

    return render(
        request,
        "assets/handover.html",
        {
            "handover_assets": handover_assets,
            "returned_assets": returned_assets,
            "employees": employees,
        },
    )


@login_required
@hr_required
def asset_handover(request):
    if request.method == "POST":
        asset = Asset()
        asset.name = request.POST.get("name")
        asset.custody_type = request.POST.get("custody_type")
        asset.serial_number = request.POST.get("serial_number", "")
        asset.model_number = request.POST.get("model_number", "")
        asset.condition_on_handover = request.POST.get("condition_on_handover", "")
        asset.notes = request.POST.get("notes", "")
        asset.assigned_to_id = request.POST.get("assigned_to_id")
        asset.assigned_date = request.POST.get("assigned_date")
        asset.expected_return_date = request.POST.get("expected_return_date") or None
        asset.is_returned = False  # Important: Set to False for handover
        asset.created_by = request.user

        if asset.assigned_to_id:
            asset.save()
            messages.success(request, f'Asset "{asset.name}" handed over successfully.')
        else:
            messages.error(request, "Please select an employee.")

        return redirect("asset_handover_list")

    return redirect("asset_handover_list")


@login_required
@hr_required
def asset_return(request):
    if request.method == "POST":
        asset_id = request.POST.get("asset_id")
        try:
            asset = Asset.objects.get(id=asset_id)
            asset.returned_date = request.POST.get("returned_date")
            asset.condition_on_return = request.POST.get("condition_on_return")
            asset.is_returned = True  # Important: Set to True when returned
            if request.POST.get("notes"):
                asset.notes = (
                    f"{asset.notes}\n\nReturn Notes: {request.POST.get('notes')}"
                )
            asset.save()
            messages.success(request, f'Asset "{asset.name}" returned successfully.')
        except Asset.DoesNotExist:
            messages.error(request, "Asset not found.")

        return redirect("asset_handover_list")

    return redirect("asset_handover_list")


@login_required
@employee_owner_or_hr_required
def employee_documents(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    documents = employee.documents.all().order_by("-created_at")

    if request.method == "POST" and request.user.is_hr:
        form = EmployeeDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.employee = employee
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, "Document uploaded successfully.")
            return redirect("employee_documents", pk=employee.pk)
    else:
        form = EmployeeDocumentForm()

    return render(
        request,
        "employee/documents.html",
        {
            "employee": employee,
            "documents": documents,
            "form": form,
            "active_tab": "documents",
        },
    )


@login_required
@hr_required
def delete_document(request, pk):
    doc = get_object_or_404(EmployeeDocument, pk=pk)
    employee_pk = doc.employee.pk
    doc.delete()
    messages.success(request, "Document deleted successfully.")
    return redirect("employee_documents", pk=employee_pk)


def check_expiring_documents():
    today = timezone.now().date()
    # Documents expiring in next 30 days
    expiring_soon = EmployeeDocument.objects.filter(
        expiry_date__isnull=False,
        expiry_date__gte=today,
        expiry_date__lte=today + timezone.timedelta(days=30),
    )

    for doc in expiring_soon:
        employee = doc.employee
        days_left = (doc.expiry_date - today).days

        subject = f"Document Expiry Alert: {doc.get_document_type_display()}"

        message = f"""
        Dear {employee.full_name},
        
        Your {doc.get_document_type_display()} (Number: {doc.document_number}) will expire on {doc.expiry_date}.
        Days remaining: {days_left} days.
        
        Please renew your document before the expiry date.
        
        Best regards,
        HR Department
        """

        # Send to employee
        if employee.email:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [employee.email])

        # Send to HR
        hr_emails = (
            Employee.objects.filter(role="hr", email__isnull=False)
            .exclude(email="")
            .values_list("email", flat=True)
        )
        if hr_emails:
            hr_message = f"""
            Alert: Employee Document Expiring
            
            Employee: {employee.full_name}
            Document: {doc.get_document_type_display()}
            Number: {doc.document_number}
            Expiry Date: {doc.expiry_date}
            Days Remaining: {days_left}
            """
            send_mail(subject, hr_message, settings.DEFAULT_FROM_EMAIL, list(hr_emails))


# ─── Advance Salary Helpers ───────────────────────────────────────────────────

def _get_advance_requester_role(user):
    """
    Detect requester role for advance salary flow.
    Uses advance_role for top_manager, role field for hr, else 'other'.
    """
    if user.advance_role in ("top_manager","accountant"):
        return "top_manager"
    if user.role == "hr":
        return "hr"
    return "other"


def _can_approve_advance(user, adv):
    """
    Returns True if it is this user's turn to approve.

    Flow A — top_manager requester:
        submitted → hr_approved → ceo_approved → bank_approved → paid

    Flow B — hr requester:
        submitted → accountant_approved → ceo_approved → bank_approved → paid

    Flow C — other requester:
        submitted → hr_approved → sub_accountant_approved → accountant_approved → bank_approved → paid

    Gate: each approver only sees the request when the PREVIOUS stage is done.
    """
    state = adv.approval_state
    rr = adv.requester_role

    if state in ("draft", "paid", "rejected"):
        return False

    # HR approves:
    #   Flow A: submitted
    #   Flow C: submitted
    if user.role == "hr":
        if rr == "top_manager" and state == "submitted":
            return True
        if rr == "other" and state == "submitted":
            return True
        return False

    # Accountant approves:
    #   Flow B: submitted
    #   Flow C: hr_approved
    if user.advance_role == "accountant":
        if rr == "hr" and state == "submitted":
            return True
        if rr == "other" and state == "hr_approved":
            return True
        return False

    # Sub Accountant approves:
    # Flow C only: hr_approved → sub_accountant_approved
    if user.advance_role == "sub_accountant":
        if rr == "other" and state == "hr_approved":
            return True
        return False

    # CEO approves:
    #   Flow A: hr_approved
    #   Flow B: accountant_approved
    if user.role == "ceo":
        if rr == "top_manager" and state == "hr_approved":
            return True
        if rr == "hr" and state == "accountant_approved":
            return True
        return False

    # Bank User — final step in all flows:
    #   Flow A: ceo_approved
    #   Flow B: ceo_approved
    #   Flow C: accountant_approved
    if user.advance_role == "bank_user":
        if rr in ("top_manager", "hr") and state == "ceo_approved":
            return True
        if rr == "other" and state == "accountant_approved":
            return True
        return False

    return False


def _can_refuse_advance(user, adv):
    """Refuse allowed only at the same stage the user can approve."""
    if adv.approval_state in ("draft", "paid", "rejected"):
        return False
    return _can_approve_advance(user, adv)


def _get_next_advance_state(user, adv):
    """Returns the next approval_state after this user approves."""
    rr = adv.requester_role
    state = adv.approval_state

    # Flow A: top_manager
    if rr == "top_manager":
        if state == "submitted":
            return "hr_approved"        # HR just approved
        if state == "hr_approved":
            return "ceo_approved"       # CEO just approved
        if state == "ceo_approved":
            return "bank_approved"      # Bank just approved → paid

    # Flow B: hr
    if rr == "hr":
        if state == "submitted":
            return "accountant_approved"  # Accountant just approved
        if state == "accountant_approved":
            return "ceo_approved"         # CEO just approved
        if state == "ceo_approved":
            return "bank_approved"        # Bank just approved → paid

    # Flow C: other
    if rr == "other":
        if state == "submitted":
            return "hr_approved"               # HR just approved
        if state == "hr_approved":
            return "sub_accountant_approved"   # Sub Accountant just approved
        if state == "sub_accountant_approved":
            return "accountant_approved"       # Accountant just approved
        if state == "accountant_approved":
            return "bank_approved"             # Bank just approved → paid

    return None


# ─── Advance Salary Views ─────────────────────────────────────────────────────

@login_required
def advance_salary_list(request):
    user = request.user
    role = user.role
    advance_role = user.advance_role

    # Build queryset — each role sees ONLY their own + requests where it's their turn
    if role == "hr":
        # HR sees own requests + submitted top_manager requests (Flow A)
        # + submitted other requests (Flow C)
        qs = AdvanceSalaryRequest.objects.filter(
            Q(employee=user) |
            Q(approval_state="submitted", requester_role="top_manager") |
            Q(approval_state="submitted", requester_role="other") |
            Q(approval_state__in=["bank_approved", "paid", "rejected"])
        )

    elif advance_role == "accountant":
        # Accountant sees own requests
        # + Flow B: submitted hr requests
        # + Flow C: hr_approved other requests
        qs = AdvanceSalaryRequest.objects.filter(
            Q(employee=user) |
            Q(approval_state="submitted", requester_role="hr") |
            Q(approval_state="hr_approved", requester_role="other")
        )

    elif advance_role == "sub_accountant":
        # Sub Accountant sees own requests
        # + Flow C only: hr_approved other requests
        qs = AdvanceSalaryRequest.objects.filter(
            Q(employee=user) |
            Q(approval_state="hr_approved", requester_role="other")
        )

    elif role == "ceo":
        # CEO sees own requests
        # + Flow A: hr_approved top_manager requests
        # + Flow B: accountant_approved hr requests
        qs = AdvanceSalaryRequest.objects.filter(
            Q(employee=user) |
            Q(approval_state="hr_approved", requester_role="top_manager") |
            Q(approval_state="accountant_approved", requester_role="hr")
        )

    elif advance_role == "bank_user":
        # Bank sees own requests
        # + Flow A & B: ceo_approved requests
        # + Flow C: accountant_approved other requests
        qs = AdvanceSalaryRequest.objects.filter(
            Q(employee=user) |
            Q(approval_state="ceo_approved", requester_role__in=["top_manager", "hr"]) |
            Q(approval_state="accountant_approved", requester_role="other")
        )

    else:
        # Everyone else sees only their own requests
        qs = AdvanceSalaryRequest.objects.filter(employee=user)

    qs = qs.select_related("employee").order_by("-created_at").distinct()

    # Annotate approve/refuse flags per request
    for adv in qs:
        adv.user_can_approve = _can_approve_advance(user, adv)
        adv.user_can_refuse = _can_refuse_advance(user, adv)

    status_filter = request.GET.get("status", "")
    if status_filter:
        qs = qs.filter(status=status_filter)

    return render(request, "advance_salary/list.html", {
    "advances": qs,
    "status_filter": status_filter,
    })


@login_required
def advance_salary_create(request):
    form = AdvanceSalaryRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.employee = request.user
        obj.requester_role = _get_advance_requester_role(request.user)
        obj.approval_state = "submitted"
        obj.status = "pending"
        obj.save()
        messages.success(request, "Advance salary request submitted successfully.")
        return redirect("advance_salary_list")
    return render(request, "advance_salary/create.html", {"form": form})


@login_required
def advance_salary_approve(request, pk):
    adv = get_object_or_404(AdvanceSalaryRequest, pk=pk)
    user = request.user

    if not _can_approve_advance(user, adv):
        messages.error(request, "You are not authorised to approve this request at its current stage.")
        return redirect("advance_salary_list")

    next_state = _get_next_advance_state(user, adv)

    if next_state == "bank_approved":
        # Bank user final approval → mark as paid
        adv.approval_state = "bank_approved"
        adv.status = "paid"
        adv.reviewed_by = user
        adv.reviewed_at = timezone.now()
        messages.success(request, "Final approval done. Marked as paid.")
    else:
        adv.approval_state = next_state
        adv.reviewed_by = user
        adv.reviewed_at = timezone.now()
        messages.success(request, f"Approved. Forwarded to next stage.")

    adv.save()
    return redirect("advance_salary_list")


@login_required
def advance_salary_refuse(request, pk):
    adv = get_object_or_404(AdvanceSalaryRequest, pk=pk)
    user = request.user

    if not _can_refuse_advance(user, adv):
        messages.error(request, "You are not authorised to refuse this request at its current stage.")
        return redirect("advance_salary_list")

    reason = request.POST.get("reason", "").strip()
    adv.approval_state = "rejected"
    adv.status = "rejected"
    adv.hr_notes = reason
    adv.reviewed_by = user
    adv.reviewed_at = timezone.now()
    adv.save()
    messages.success(request, "Request rejected.")
    return redirect("advance_salary_list")


@login_required
def advance_salary_review(request, pk):
    """Detail view — read only for everyone, HR notes editable only for HR."""
    adv = get_object_or_404(AdvanceSalaryRequest, pk=pk)
    user = request.user
    can_approve = _can_approve_advance(user, adv)
    can_refuse = _can_refuse_advance(user, adv)

    if request.method == "POST" and user.role == "hr":
        adv.hr_notes = request.POST.get("hr_notes", "")
        adv.save()
        messages.success(request, "Notes saved.")
        return redirect("advance_salary_review", pk=pk)

    return render(request, "advance_salary/review.html", {
        "advance": adv,
        "can_approve": can_approve,
        "can_refuse": can_refuse,
    })
@login_required
@hr_required
def advance_salary_delete(request, pk):
    advance = get_object_or_404(AdvanceSalaryRequest, pk=pk)
    advance.delete()
    messages.success(request, "Advance request deleted.")
    return redirect("advance_salary_list")