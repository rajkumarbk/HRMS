# HRMS — HR Management System
A full-featured HR Management System built with Django, designed for Saudi companies.

---

## 🚀 Quick Setup

### 1. Clone / Extract the Project
```bash
cd hr_system
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Migrations
```bash
python manage.py migrate
```

### 5. Create Admin Account
```bash
python manage.py shell
```
```python
from core.models import Employee
Employee.objects.create_superuser(
    iqama_number='YOUR_IQAMA',
    password='YOUR_PASSWORD',
    full_name='Your Name'
)
```

### 6. Run the Server
```bash
python manage.py runserver
```
Open: http://127.0.0.1:8000

---

## 🔐 Default Login (Demo)
| Iqama Number | Password | Role |
|---|---|---|
| 1000000000 | admin1234 | Administrator |
| 2000000001 | emp12345 | Sample Employee |

---

## 📦 Features

### 1. Employee Information
- Personal Info (name, iqama, nationality, DOB, gender, marital status)
- Contact Info (mobile, email, address, emergency contact)
- Work Info (job title, department, branch, contract, schedule)
- Financial Info (salary, allowances, bank details, IBAN)

### 2. Time Off
- Leave request submission
- Manager approval / refusal workflow
- Multiple leave types (Annual, Sick, Emergency, Hajj)

### 3. Attendance (ZKTeco)
- Add ZKTeco devices by IP & Port
- Sync attendance records
- View daily attendance log
- Install `pyzk` for real machine sync

### 4. Discuss
- Direct messaging between employees
- Announcements (HR/Admin only)
- Real-time feel with auto-scroll

---

## 🖥️ ZKTeco Real Sync Setup

```bash
pip install pyzk
```

Then in `core/views.py`, update `attendance_sync`:
```python
from zk import ZK

def attendance_sync(request, device_id):
    device = get_object_or_404(ZKTecoDevice, pk=device_id)
    zk = ZK(device.ip_address, port=device.port, timeout=5)
    conn = zk.connect()
    attendances = conn.get_attendance()
    for att in attendances:
        emp = Employee.objects.filter(employee_id=str(att.user_id)).first()
        if emp:
            AttendanceRecord.objects.update_or_create(
                employee=emp, date=att.timestamp.date(),
                defaults={'check_in': att.timestamp}
            )
    conn.disconnect()
    device.last_sync = timezone.now()
    device.save()
    return redirect('attendance_list')
```

---

## 🌐 Production Deployment (DigitalOcean)

```bash
# Install nginx + gunicorn
pip install gunicorn

# Run
gunicorn config.wsgi:application --bind 0.0.0.0:8000

# Collect static files
python manage.py collectstatic

# Update settings.py for production:
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']
DATABASES = {  # Use PostgreSQL
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'hrms_db',
        'USER': 'hrms_user',
        'PASSWORD': 'yourpassword',
        'HOST': 'localhost',
    }
}
```

---

## 📁 Project Structure
```
hr_system/
├── config/             # Django settings & URLs
├── core/               # Main app (models, views, forms)
│   ├── models.py       # All data models
│   ├── views.py        # All views
│   ├── forms.py        # Form classes
│   ├── backends.py     # Iqama auth backend
│   └── context_processors.py
├── templates/          # HTML templates
│   ├── base.html       # Base layout with sidebar
│   ├── auth/login.html
│   ├── dashboard.html
│   ├── employee/
│   ├── timeoff/
│   ├── attendance/
│   └── discuss/
├── static/
│   └── css/main.css    # All styling
└── requirements.txt
```
