# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - 2026-11-23

### Added

- Caught-and-logged errors reach Bugstack. An `except` block that calls
  `logger.exception(...)` or `logger.error("... %s", exc)` and carries on
  was invisible: only `sys.excepthook`, the framework middleware and
  `capture_exception` reported anything. Once `bugstack.init()` has run, an
  ERROR record carrying an exception is reported, anchored at the logging
  call. On by default; `capture_logging=False` turns it off and
  `capture_log_messages=True` also forwards ERROR records without an
  exception. Log output is unchanged (the SDK wraps
  `logging.Logger.callHandlers` and adds no handler, so
  `logging.basicConfig()` still works after `init()`). Capped at 20 a minute
  and once per site and message per 5 minutes, redacted with
  `redact_fields`, never raises.

## [1.2.0] - 2026-10-28

### Fixed

- The default endpoint is now `https://dashboard.bugstack.ai/api/ingest/sdk`.
  It was `https://api.bugstack.dev/api/capture`, which is not Bugstack's
  ingest address, so events sent with the default setting did not reach
  Bugstack. Apps that pass `endpoint=` themselves are unaffected.
- The package's homepage, documentation, repository and contact links now
  point at bugstack.ai and github.com/Bugstackai/Bugstack-SDK-Python.

## [1.0.0] - 2026-02-13

### Added

- Core SDK with `bugstack.init()` and `bugstack.capture_exception()`
- Background HTTP transport with retry and exponential backoff
- SHA-256 error fingerprinting and client-side deduplication
- `before_send` hook for event inspection/modification/filtering
- `ignored_errors` for skipping specific error types or messages
- `dry_run` mode for transparent debugging
- `enabled` kill switch
- FastAPI middleware integration
- Django middleware integration with auto-init from settings
- Flask integration via `init_app()`
- Generic integration via `sys.excepthook` and `threading.excepthook`
