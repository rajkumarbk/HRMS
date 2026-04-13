from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from core.models import EmployeeDocument, Employee

class Command(BaseCommand):
    help = 'Check for expiring documents and send email alerts'
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        expiring_soon = EmployeeDocument.objects.filter(
            expiry_date__isnull=False,
            expiry_date__gte=today,
            expiry_date__lte=today + timezone.timedelta(days=30)
        )
        
        for doc in expiring_soon:
            employee = doc.employee
            days_left = (doc.expiry_date - today).days
            
            subject = f"Document Expiry Alert: {doc.get_document_type_display()}"
            
            # Send to employee
            if employee.email:
                send_mail(subject, f"Your {doc.get_document_type_display()} expires in {days_left} days.", settings.DEFAULT_FROM_EMAIL, [employee.email])
            
            # Send to HR
            hr_emails = Employee.objects.filter(role='hr', email__isnull=False).exclude(email='').values_list('email', flat=True)
            if hr_emails:
                send_mail(subject, f"{employee.full_name}'s {doc.get_document_type_display()} expires in {days_left} days.", settings.DEFAULT_FROM_EMAIL, list(hr_emails))
        
        self.stdout.write(self.style.SUCCESS(f'Checked {expiring_soon.count()} expiring documents'))