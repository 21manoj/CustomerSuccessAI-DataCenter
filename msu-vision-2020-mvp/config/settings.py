"""
MSU Vision 2020 — MVP settings (aligns with architecture v1.2 §9–§10).
Use Python 3.12 + Django 5.1 in production when available.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only-change-in-production")
DEBUG = env("DEBUG", default=True)
# Show username/password hint for seeded `demo` user on /accounts/login/ (set False for strict production).
SHOW_DEMO_LOGIN_HELP = env.bool("SHOW_DEMO_LOGIN_HELP", default=True)
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "testserver", ".elasticbeanstalk.com"],
)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# CloudFront → nginx (HTTP origin): trust X-Forwarded-Proto for secure cookies / redirects.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Subpath on shared host (e.g. https://your-cf-host/msu2020/) — set FORCE_SCRIPT_NAME=/msu2020
_force = (env("FORCE_SCRIPT_NAME", default="") or "").strip().rstrip("/")
FORCE_SCRIPT_NAME = _force if _force else None
if FORCE_SCRIPT_NAME:
    STATIC_URL = f"{FORCE_SCRIPT_NAME}/static/"
    MEDIA_URL = f"{FORCE_SCRIPT_NAME}/media/"
    SESSION_COOKIE_PATH = f"{FORCE_SCRIPT_NAME}/"
    CSRF_COOKIE_PATH = f"{FORCE_SCRIPT_NAME}/"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third party
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "django_htmx",
    "widget_tweaks",
    "django_filters",
    # Local
    "apps.core.apps.CoreConfig",
    "apps.stakeholders.apps.StakeholdersConfig",
    "apps.needs.apps.NeedsConfig",
    "apps.projects.apps.ProjectsConfig",
    "apps.funding.apps.FundingConfig",
    "apps.events.apps.EventsConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.programs.apps.ProgramsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.ensure_user_profile_middleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.demo_login_banner",
            ],
        },
    },
]

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Allow multi-file need uploads (see apps.needs.attachments.MAX_ATTACHMENT_BYTES)
DATA_UPLOAD_MAX_MEMORY_SIZE = 26 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 26 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "/accounts/login/"

ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": env("GOOGLE_CLIENT_ID", default=""),
            "secret": env("GOOGLE_CLIENT_SECRET", default=""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")

# Architecture §5.3 / §10.2 — USD-equivalent governance thresholds
GOVERNANCE_THRESHOLD_NEED_USD = env.int("GOVERNANCE_THRESHOLD_NEED_USD", default=12000)
GOVERNANCE_THRESHOLD_PROJECT_USD = env.int("GOVERNANCE_THRESHOLD_PROJECT_USD", default=12000)
GOVERNANCE_THRESHOLD_EXPENSE_USD = env.int("GOVERNANCE_THRESHOLD_EXPENSE_USD", default=2500)

# Static FX for MVP (replace with API in production)
MVP_EXCHANGE_RATES_TO_USD = {
    "USD": "1",
    "INR": "0.012",
}

FEATURE_EMAIL_INGESTION = env.bool("FEATURE_EMAIL_INGESTION", default=False)
