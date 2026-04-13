from .models import TimeOffRequest, Message, AdvanceSalaryRequest


def notification_counts(request):
    if request.user.is_authenticated:
        return {
            "pending_count": TimeOffRequest.objects.filter(status="pending").count(),
            "unread_count": Message.objects.filter(
                receiver=request.user, is_read=False
            ).count(),
            "pending_advance_count": (
                AdvanceSalaryRequest.objects.filter(status="pending").count()
                if request.user.is_hr
                else 0
            ),
        }
    return {
        "pending_count": 0,
        "unread_count": 0,
        "pending_advance_count": 0,
    }