from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Send password reset email'
    
    def add_arguments(self, parser):
        parser.add_argument('email', type=str)
        parser.add_argument('reset_link', type=str)
        parser.add_argument('employee_name', type=str)
    
    def handle(self, *args, **options):
        email = options['email']
        reset_link = options['reset_link']
        employee_name = options['employee_name']
        
        subject = 'Password Reset Request - HRMS'
        message = f"""
        Dear {employee_name},
        
        You have requested to reset your password for the HR Management System.
        
        Click the link below to reset your password:
        {reset_link}
        
        This link will expire in 24 hours.
        
        If you did not request this, please ignore this email or contact IT support.
        
        Best regards,
        HRMS Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
        self.stdout.write(self.style.SUCCESS(f'Password reset email sent to {email}'))