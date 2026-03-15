from functools import wraps
from django.shortcuts import redirect


def superuser_required(view_func):
    """Redirect non-superusers to the panel login page."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("panel:login")
        if not request.user.is_superuser:
            return redirect("panel:login")
        return view_func(request, *args, **kwargs)
    return wrapper
