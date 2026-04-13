from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

Employee = get_user_model()

class Command(BaseCommand):
    help = 'Set a user as HR'
    
    def add_arguments(self, parser):
        parser.add_argument('iqama_number', type=str, help='User iqama number')
    
    def handle(self, *args, **options):
        iqama_number = options['iqama_number']
        try:
            user = Employee.objects.get(iqama_number=iqama_number)
            user.role = 'hr'
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully set {user.full_name} as HR'))
        except Employee.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with iqama {iqama_number} not found'))