# bugstack-python

Official Python SDK for [BugStack](https://bugstack.dev) — capture, report, and auto-fix production errors.

[![PyPI](https://img.shields.io/pypi/v/bugstack)](https://pypi.org/project/bugstack/)
[![Python](https://img.shields.io/pypi/pyversions/bugstack)](https://pypi.org/project/bugstack/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Installation

```bash
pip install bugstack
```

## Quick Start

```python
import bugstack

bugstack.init(api_key="bs_live_...")

try:
    risky_operation()
except Exception as e:
    bugstack.capture_exception(e)
```

## Framework Integrations

### FastAPI

```python
from fastapi import FastAPI
from bugstack.integrations.fastapi import FastAPIMiddleware

app = FastAPI()
app.add_middleware(FastAPIMiddleware)

bugstack.init(api_key="bs_live_...")
```

### Django

```python
# settings.py
MIDDLEWARE = [
    'bugstack.integrations.django.BugStackMiddleware',
    # ... other middleware
]

BUGSTACK_API_KEY = "bs_live_..."
BUGSTACK_AUTO_FIX = True  # optional
```

### Flask

```python
from flask import Flask
from bugstack.integrations.flask import init_app

app = Flask(__name__)
bugstack.init(api_key="bs_live_...")
init_app(app)
```

### Generic (sys.excepthook)

```python
from bugstack.integrations.generic import install_hooks

bugstack.init(api_key="bs_live_...")
install_hooks()
```

## Configuration

```python
bugstack.init(
    api_key="bs_live_...",          # Required
    environment="production",       # Default: "production"
    auto_fix=True,                  # Enable AI-powered auto-fix
    debug=False,                    # Log SDK activity
    dry_run=False,                  # Log without sending
    enabled=True,                   # Kill switch
    deduplication_window=300,       # Seconds (default: 5 min)
    timeout=5.0,                    # HTTP timeout in seconds
    max_retries=3,                  # Retry attempts
    ignored_errors=[                # Errors to skip
        KeyboardInterrupt,
        "expected error message",
    ],
    before_send=my_hook,            # Inspect/modify/drop events
    redact_fields=["password"],     # Fields to redact
)
```

## Data Transparency

### `before_send` Hook

Inspect, modify, or drop any event before it leaves your application:

```python
def before_send(event):
    # Drop health check errors
    if "health" in event.request.route:
        return None

    # Redact sensitive data
    event.metadata.pop("secret", None)

    return event

bugstack.init(api_key="bs_live_...", before_send=before_send)
```

### `ignored_errors`

Skip specific error types or messages:

```python
bugstack.init(
    api_key="bs_live_...",
    ignored_errors=[
        KeyboardInterrupt,          # By type
        SystemExit,                 # By type
        "Connection reset",         # By exact message
    ],
)
```

### `dry_run` Mode

See exactly what would be sent without making any network requests:

```python
bugstack.init(api_key="bs_live_...", dry_run=True)
# Prints: [BugStack DryRun] Would send: { ... }
```

## What Gets Sent

Every error event contains exactly this — nothing more:

```json
{
  "apiKey": "bs_live_...",
  "error": {
    "message": "division by zero",
    "stackTrace": "Traceback (most recent call last)...",
    "file": "app/api/handler.py",
    "function": "process_request",
    "fingerprint": "a1b2c3d4e5f6g7h8"
  },
  "environment": {
    "language": "python",
    "languageVersion": "3.12.1",
    "framework": "fastapi",
    "frameworkVersion": "0.109.0",
    "os": "linux",
    "sdkVersion": "1.0.0"
  },
  "timestamp": "2026-01-15T08:30:00+00:00"
}
```

No cookies. No IP addresses. No user data. No request bodies (unless you explicitly include them).

## License

MIT — see [LICENSE](LICENSE).
