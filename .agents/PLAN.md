# Session Plan — 2026-03-31

## Goal
Implement task 1 (configurable CORS with local-safe defaults) using TDD, including config wiring and regression tests.

## Tasks
- [x] Write failing API tests for CORS default behavior (allowed local origin + blocked non-local origin, including preflight) (td:td-1e0c4f)
- [x] Write failing API tests for env-configured CORS override behavior (td:td-1e0c4f)
- [x] Implement CORS settings in `src/app/core/config.py` and replace hardcoded middleware config in `src/main.py` (td:td-1e0c4f)
- [x] Update `.env.example`, `docker-compose.yml`, `docker-compose.postgres.yml`, and docs to expose new CORS env vars (td:td-1e0c4f)
- [x] Run targeted and full relevant test suites, fix failures, and confirm behavior (td:td-1e0c4f)

## Notes
- Beads sync is currently blocked in this environment because `bd` requires Dolt and the local `bd` database cannot be opened.
- Active tracker for this session is `td`; first task is `td-1e0c4f`.
- TDD order is strict: tests first, then implementation, then validation.
