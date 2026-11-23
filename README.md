# bugstack-python

The [Bugstack](https://bugstack.ai) SDK for Python: Django, Flask and FastAPI.

Bugstack is autonomous software maintenance. It watches your app and your repository, fixes what breaks, and sends every change as a pull request you control. This SDK is how your app tells Bugstack about an uncaught server error.

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

### Caught-and-logged errors (`logging`)

Most failures never reach `sys.excepthook`. An `except` block logs them and the app carries on:

```python
try:
    grant_credits(order)
except KeyError:
    logger.exception("[billing] grant failed")   # a log line nobody reads
```

Once `bugstack.init()` has run, these reach Bugstack too. It is on by default and needs no handler: every log record still goes to your handlers exactly as before, and `logging.basicConfig()` still works after `init()`.

- **Forwarded:** an ERROR (or higher) record that carries an exception, as `exc_info` (`logger.exception(...)`, `exc_info=True`) or as a `%` argument (`logger.error("row failed: %s", exc)`). The report is anchored at the logging call, so each logging site is its own issue.
- **Left as a log line:** ERROR records with no exception (set `capture_log_messages=True` to forward them as their message), the SDK's own `bugstack` logger, and an exception `capture_exception` already sent.
- **Bounded:** at most 20 a minute per process, the same site and message at most once per 5 minutes, then the usual fingerprint dedup. The logged text goes through `redact_fields`, and bearer tokens are masked. Forwarding never raises.

```python
bugstack.init(api_key="bs_live_...", capture_logging=False)        # turn it off
bugstack.init(api_key="bs_live_...", capture_log_messages=True)    # also forward message-only ERROR records
```

## Configuration

```python
bugstack.init(
    api_key="bs_live_...",          # Required
    environment="production",       # Default: "production"
    auto_fix=True,                  # Let Bugstack open a fix for errors this SDK reports
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
    capture_logging=True,           # Forward caught-and-logged errors (default: on)
    capture_log_messages=False,     # Also forward ERROR records without an exception
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
