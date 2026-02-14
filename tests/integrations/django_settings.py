"""Minimal Django settings for testing BugStack middleware."""

SECRET_KEY = "test-secret-key-not-for-production"
DEBUG = True
INSTALLED_APPS = []
MIDDLEWARE = []

BUGSTACK_API_KEY = "bs_test_django_key"
BUGSTACK_AUTO_FIX = False
BUGSTACK_ENVIRONMENT = "test"
BUGSTACK_DEBUG = False
BUGSTACK_DRY_RUN = True
