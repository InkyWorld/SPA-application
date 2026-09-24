"""Project settings. Single file on purpose: 12-factor via env, no over-engineering."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str = "") -> str:
    """Read a string setting from the environment.

    Args:
        name: Environment variable name.
        default: Value used when the variable is missing.

    Returns:
        Variable value or the default.
    """
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean setting from the environment.

    Args:
        name: Environment variable name.
        default: Value used when the variable is missing.

    Returns:
        True for "1"/"true"/"yes" (case-insensitive), else False.
    """
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "*").split(",") if h]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "channels",
    "captcha",
    "drf_spectacular",
    "apps.comments",
]

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

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ]},
    }
]

# PostgreSQL only — no SQLite fallback (tests and runs use the same engine).
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": env("POSTGRES_DB", "comments"),
    "USER": env("POSTGRES_USER", "comments"),
    "PASSWORD": env("POSTGRES_PASSWORD", "comments"),
    "HOST": env("POSTGRES_HOST", "localhost"),
    "PORT": env("POSTGRES_PORT", "5432"),
}}

REDIS_URL = env("REDIS_URL", "")

if REDIS_URL:
    CACHES = {"default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }}
    CHANNEL_LAYERS = {"default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }}
else:  # local dev / tests: no services required
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min"},
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SPA Comments API",
    "DESCRIPTION": "Test assignment: nested comments with captcha, files and JWT.",
    "VERSION": "1.0.0",
}

# --- Celery (queue) ---
CELERY_BROKER_URL = REDIS_URL or "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_EAGER", True)
CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-captchas": {
        "task": "apps.comments.tasks.cleanup_expired_captchas",
        "schedule": 300.0,
    },
}

# --- Comments list cache (TTL 5 min, version-bumped on every create) ---
COMMENTS_LIST_CACHE_TTL = 300

# --- Comments domain limits (single source of truth) ---
COMMENTS_PAGE_SIZE = 25
IMAGE_MAX_SIZE = (320, 240)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
TEXT_FILE_MAX_BYTES = 100 * 1024

# --- django-simple-captcha (DB store; length/timeout mirror previous UX) ---
CAPTCHA_LENGTH = 5
CAPTCHA_TIMEOUT = 5  # minutes
CAPTCHA_CHALLENGE_FUNCT = "apps.comments.services.captcha.alnum_challenge"

CORS_ALLOW_ALL = env_bool("CORS_ALLOW_ALL", True)
if CORS_ALLOW_ALL:
    MIDDLEWARE.insert(2, "config.middleware.AllowAllCorsMiddleware")
