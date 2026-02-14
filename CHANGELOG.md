# Changelog

All notable changes to this project will be documented in this file.

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
