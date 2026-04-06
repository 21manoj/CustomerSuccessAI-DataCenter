from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

User = get_user_model()


@require_POST
def demo_login(request):
    """One-click demo user — only when DEBUG (never expose in production)."""
    if not settings.DEBUG:
        raise Http404()
    user = User.objects.filter(username="demo").first()
    if not user:
        messages.error(
            request,
            'No demo user yet. Run: python manage.py load_demo_data',
        )
        return redirect("account_login")
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("dashboard:home")
