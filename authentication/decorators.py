from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def basic_user_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        if (
            not request.user.is_active
            or request.user.is_staff
            or request.user.is_superuser
        ):
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper