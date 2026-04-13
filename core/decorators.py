# decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def hr_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not request.user.is_hr:
            messages.error(
                request,
                "You do not have permission to access this page. HR access required.",
            )
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper


def employee_owner_or_hr_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        # Get pk from kwargs
        pk = kwargs.get("pk")
        # HR can access any employee
        if request.user.is_hr:
            return view_func(request, *args, **kwargs)
        # Regular employee can only access their own profile
        if pk and str(request.user.pk) != str(pk):
            messages.error(request, "You can only view and edit your own information.")
            return redirect("employee_detail", pk=request.user.pk)
        return view_func(request, *args, **kwargs)

    return wrapper
