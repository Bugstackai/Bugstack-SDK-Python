# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

**Email:** security@bugstack.ai

Please do **not** open a public GitHub issue for security vulnerabilities.

We will respond within 48 hours and work with you to understand and address the issue.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |

## Security Design

- The SDK never captures request bodies, headers, cookies, or IP addresses by default
- All data transmission uses HTTPS
- The `before_send` hook lets you inspect and filter every event before it leaves your application
- The `dry_run` mode lets you verify exactly what would be sent
- The SDK never throws exceptions — all errors are caught internally
