# Session Plan — 2026-03-31

## Goal
Implement safe async task boundaries for note embedding jobs so background execution never uses request-scoped DB sessions/ORM objects.

## Tasks
- [x] Add failing tests that prove async note embedding paths pass primitive IDs/payloads only and create fresh DB sessions in task execution (td:td-0717d4)
- [x] Refactor note async embedding scheduling/execution to remove request-scoped session/ORM leakage and use task-safe inputs (td:td-0717d4)
- [x] Add/adjust structured failure logging and retry metadata assertions for the async note embedding path (td:td-0717d4)
- [x] Run targeted and relevant full tests, then resolve regressions (td:td-0717d4)

## Notes
- Carry-over target from HANDOFF is `td-0717d4` and this session is scoped only to that item.
- `bd` sync is currently blocked in this environment (Dolt missing/unreachable), so issue status could not be updated from this shell.
- TDD order remains strict: tests first, then implementation, then verification.
