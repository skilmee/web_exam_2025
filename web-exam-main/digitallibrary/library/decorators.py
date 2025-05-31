from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def login_required_with_message(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Для выполнения данного действия необходимо пройти процедуру аутентификации.")
            return redirect(f'/login/?next={request.path}')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def role_required(*roles):
    def decorator(view_func):
        @login_required_with_message
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if hasattr(user, 'role'):
                if user.role.name in roles or user.role.id in roles:
                    return view_func(request, *args, **kwargs)

            messages.warning(request, "У вас недостаточно прав для выполнения данного действия.")
            return redirect('home')
        return _wrapped_view
    return decorator
