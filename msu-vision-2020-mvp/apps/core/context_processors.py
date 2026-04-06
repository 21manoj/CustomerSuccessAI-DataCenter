from django.conf import settings


def demo_login_banner(request):
    """Expose whether to show seeded demo credentials on the login page."""
    return {"show_demo_login_help": getattr(settings, "SHOW_DEMO_LOGIN_HELP", True)}
