# PRD: Reliability and Security Hardening for AI Agent Memory System

## Problem
The current system is functionally complete but has production-risk gaps in security defaults, async processing reliability, data consistency, and observability. These risks can cause silent failures, accidental unauthenticated exposure, and SQL/Qdrant drift.

## Goals
1. Make security defaults safe-by-default.
2. Make embedding/sync flows reliable and recoverable.
3. Improve operational readiness and incident visibility.
4. Close high-risk test coverage gaps.

## Non-goals
- Rewriting the API surface or changing core domain objects.
- Replacing FastAPI/SQLAlchemy/Qdrant stack.
- Full platform redesign of deployment topology.

## Scope

### 1) Security hardening
- Keep local-first posture: auth may remain disabled/fail-open for local usage.
- Preserve scope-based auth model for optional protected deployments.
- Keep CORS configurable, with path to stricter allowlists when deployment profile changes.

### 2) Async job reliability
- Prioritize safer behavior with minimal complexity: keep `sync` as default mode.
- If async mode is enabled, stop passing request-scoped `Session`/ORM objects into background tasks.
- Refactor async task inputs to primitive IDs and immutable payloads.
- Open new DB sessions inside task execution path.
- Ensure failures are captured with structured logs and retry metadata.

### 3) SQL ↔ Qdrant consistency
- Introduce durable sync state flow (outbox/job table or equivalent persisted queue).
- Record per-note sync attempts, status, and last error.
- Add retry strategy for transient embedding/Qdrant failures.
- Ensure delete/update paths cannot silently leave stale vectors.

### 4) Error handling and observability
- Replace broad `except Exception` in hot paths with specific exception handling.
- Remove print-based failure handling in services.
- Add structured logs for search fallback, sync failures, and admin operations.
- Add minimal metrics counters (sync success/failure, queue depth, auth-disabled mode).

### 5) Health/readiness and startup behavior
- Keep liveness endpoint lightweight.
- Add readiness endpoint with DB + Qdrant checks.
- Add dependency startup retry/backoff (bounded) and clear fatal logs.

### 6) Input validation alignment
- Enforce schema constraints matching DB lengths for title/tags.
- Normalize/dedupe tags before persistence.
- Map integrity conflicts to 409/422 instead of 500.

### 7) Test coverage expansion
- Add tests for admin re-embed + unsynced repair endpoints/flows.
- Add async embedding mode tests (including failure/retry behavior).
- Add OpenAI provider-path tests with mocks.
- Add CLI command-level tests beyond transport layer.

### 8) Docs/scripts accuracy
- Align README operational commands with actual scripts/routes.
- Fix seeding/reset scripts to current API response contracts.
- Add CI smoke check for operational scripts/docs examples.

### 9) Dependency/tooling simplification
- Standardize dependency workflow on `uv` only.
- Use `pyproject.toml` + `uv.lock` as the only dependency source of truth.
- Remove duplicate dependency manifests and install paths where unnecessary.

## Requirements

### Functional requirements
-- FR1: Service must support local fail-open auth mode as a first-class configuration.
- FR2: Background embedding jobs must not depend on request lifecycle DB sessions.
- FR3: Sync status for each note must be queryable and recoverable after process restart.
- FR4: Readiness endpoint must report dependency status for SQL and Qdrant.
- FR5: Validation errors from oversized/duplicate data must return user-actionable 4xx responses.

### Non-functional requirements
- NFR1: No silent failures in embedding/search/sync paths.
- NFR2: Admin recovery operations must be idempotent and safe to re-run.
- NFR3: New tests must run in existing `make test`, `make test-integration*`, and CLI test workflows.
- NFR4: Backward compatibility for existing API routes and response contracts unless explicitly versioned.

## Success metrics
- 0 auth-disabled production incidents caused by missing key config.
- 0 known session-lifecycle errors in async embedding mode.
- <1% notes left unsynced after retry window under normal operation.
- 100% pass for new hardening test suites in CI.
- Operational docs/scripts run successfully in CI smoke stage.

## Milestones

### M1 — Security defaults (high priority)
- Auth fail-closed behavior + explicit override.
- CORS allowlist config.
- Startup warnings/fail-fast checks.

### M2 — Async + consistency core
- Background task boundary fix (IDs only + fresh sessions).
- Persisted sync-state tracking and retry policy.
- Structured error logging for sync pipeline.

### M3 — Operability and validation
- Liveness/readiness split and dependency checks.
- Input validation hardening + DB integrity mapping.
- Replace broad exception swallowing.

### M4 — Tests and tooling
- Admin/async/OpenAI path test additions.
- CLI command tests.
- README/scripts contract alignment and CI smoke checks.

## Risks
- Migration complexity if outbox/state tables are introduced.
- Behavior changes in auth defaults may break local workflows without documentation updates.
- Integration tests may become slower with expanded reliability checks.

## Dependencies
- Agreement on environment policy (`dev` vs `prod` behavior).
- Decision on async execution model (FastAPI background tasks vs dedicated queue worker).
- CI capacity for additional integration and script smoke tests.

## Open decisions for user
1. For async mode, should we keep in-process background tasks (with safe session boundaries) or defer queue adoption until needed?
2. Is backward-compatible behavior mandatory for every endpoint, or can we introduce minor contract fixes where needed?
