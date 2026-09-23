import os

os.environ.setdefault("SECRET_KEY", "test-only-key-with-at-least-thirty-two-characters")
os.environ["DEBUG"] = "True"
os.environ.setdefault("USE_SQLITE", "True")
from .settings import *  # noqa: E402,F403

SECURE_SSL_REDIRECT = False
DASHBOARD_ADMIN_EMAIL = "owner@example.com"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": [], "TEST_REQUEST_DEFAULT_FORMAT": "json"}  # noqa: F405
MIDDLEWARE = [item for item in MIDDLEWARE if not item.startswith("whitenoise.")]  # noqa: F405
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {"django.request": {"handlers": ["null"], "propagate": False}},
}
STORAGES = {**STORAGES, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}  # noqa: F405
