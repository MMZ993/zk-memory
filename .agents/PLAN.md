# Session Plan — 2026-03-31

## Goal
Replace broad exception swallowing in hot paths with targeted handling and structured logging.

## Tasks
- [x] Identify broad `except Exception` blocks in API/service hot paths and classify expected failure types (td:td-7b906c)
- [x] Implement targeted exception handling with structured logging while preserving current API contracts (td:td-7b906c)
- [x] Validate updated error-handling behavior with focused tests and local verification commands (td:td-7b906c)

## Notes
- Session scope is limited to `td-7b906c`.
- Follow-on hardening tasks from handoff remain queued for later sessions.
