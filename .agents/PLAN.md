# Session Plan — 2026-03-31

## Goal
Refactor admin async jobs to use safe task boundaries with fresh DB sessions and no request-scoped session leakage.

## Tasks
- [x] Add/adjust tests for admin async job paths to assert task-safe inputs and fresh-session execution boundaries (td:td-5266e0)
- [x] Refactor admin async scheduling/execution to pass primitive IDs/payloads only and create DB sessions inside worker execution (td:td-5266e0)
- [x] Add structured error logging and retry metadata handling for admin async failures where applicable (td:td-5266e0)
- [x] Run relevant test suites and resolve regressions for admin async job changes (td:td-5266e0)

## Notes
- Verification complete: two PRD-aligned items are now closed in `td` (`td-1e0c4f`, `td-0717d4`).
- `td-5266e0` is now marked `in_progress` for this session.
- Follow project rule: no request-scoped `Session`/ORM objects in background tasks; use IDs + fresh sessions.
- Reliability approach for this project remains intentionally simple: single-process writer assumptions (overnight admin/write jobs), no distributed lock coordination, avoid additional moving parts.
