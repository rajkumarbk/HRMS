from django.contrib.auth.backends import ModelBackend
from .models import Employee

class IqamaBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        iqama = kwargs.get('iqama_number', username)
        try:
            user = Employee.objects.get(iqama_number=iqama)
            if user.check_password(password):
                return user
        except Employee.DoesNotExist:
            return None
