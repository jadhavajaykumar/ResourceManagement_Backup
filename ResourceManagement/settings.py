import os
import socket
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ----- Core -----
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-unsafe")  # change in prod
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"

# Allow local, hostname, plus anything supplied via env var
_default_hosts = ["localhost", "127.0.0.1", socket.gethostname()]
_extra_hosts = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
ALLOWED_HOSTS = _default_hosts + _extra_hosts

# CSRF trusted origins (must include scheme + host[:port])
_default_csrf = ["http://localhost:8000", "http://127.0.0.1:8000"]
_extra_csrf = [o.strip() for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
CSRF_TRUSTED_ORIGINS = _default_csrf + _extra_csrf

# ----- Apps -----
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "accounts",
    "project",
    "expenses",
    "timesheet.apps.TimesheetConfig",
    "manager",
    "skills.apps.SkillsConfig",
    "import_export",
    "widget_tweaks",
    "crispy_forms",
    "crispy_bootstrap5",
    "employee.apps.EmployeeConfig",
    "docgen",
    "utils",
    "dashboard",
    "approvals.apps.ApprovalsConfig",
]

GRAPH_MODELS = {"all_applications": True, "group_models": True}

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

AUTH_USER_MODEL = "accounts.CustomUser"

# ----- Middleware (add WhiteNoise right after SecurityMiddleware) -----
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ResourceManagement.urls"

# (You had two DIRS keys; keep just one and include both dirs)
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates", BASE_DIR / "manager" / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]

WSGI_APPLICATION = "ResourceManagement.wsgi.application"

# ----- DB -----
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
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

# ----- Static / Media -----
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]         # source assets
STATIC_ROOT = BASE_DIR / "staticfiles"           # collectstatic output

# WhiteNoise will serve from STATIC_ROOT; keep non-manifest storage for simplicity
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"
    }
}

# (Optional) Handy in dev: lets WhiteNoise read from finders so you don't *need* collectstatic each edit.
WHITENOISE_USE_FINDERS = True

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ----- Auth redirects -----
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/accounts/profile/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# ----- Messages -----
from django.contrib.messages import constants as messages  # noqa: E402
MESSAGE_TAGS = {
    messages.DEBUG: "debug",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}

# ----- Logging (console) -----
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"": {"handlers": ["console"], "level": "INFO"}},
}

# ----- Security (HTTP in WSL) -----
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Company info (unchanged)
COMPANY_NAME = "Acme Engineering Pvt. Ltd."
COMPANY_ADDRESS = "1st Floor, Business Park, Bengaluru 560001, India"
