# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-10-28

### Fixed

- The default endpoint is now `https://dashboard.bugstack.ai/api/ingest/sdk`.
  It was `https://api.bugstack.dev/api/capture`, which is not bugstack's
  ingest address, so events sent with the default setting did not reach
  bugstack. Apps that pass `endpoint=` themselves are unaffected.
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
