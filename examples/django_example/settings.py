"""Django settings example with BugStack integration.

Add BugStackMiddleware to your MIDDLEWARE list and configure
via BUGSTACK_* settings. The middleware auto-initializes.
"""

MIDDLEWARE = [
    "bugstack.integrations.django.BugStackMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # ... other middleware
]

BUGSTACK_API_KEY = "bs_live_your_api_key_here"
BUGSTACK_AUTO_FIX = True
BUGSTACK_ENVIRONMENT = "production"
