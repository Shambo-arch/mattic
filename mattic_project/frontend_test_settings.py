"""Isolated local browser-test server. Never use these settings in production."""

from . import test_settings
from .test_settings import *  # noqa: F403

E2E_ROOT = BASE_DIR / "frontend" / ".e2e-data"  # noqa: F405
E2E_ROOT.mkdir(exist_ok=True)
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": E2E_ROOT / "db.sqlite3"}}
MEDIA_ROOT = E2E_ROOT / "media"
PRIVATE_MEDIA_ROOT = E2E_ROOT / "private_media"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DASHBOARD_ADMIN_EMAIL = "owner@e2e.example"
# Browser tests repeatedly reload multiple independent accounts from one loopback IP.
# Keep production throttling unchanged while allowing this isolated test workload.
REST_FRAMEWORK = {
    **test_settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {**test_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "auth": "1000/min"},
}
