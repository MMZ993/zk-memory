# Backlog Draft (for Beads sync)

Project: `zk_memory`
Epic candidate: `zk_memory reliability and operability hardening`

Ordered implementation tasks (dependency-first):

1. **Make CORS configurable with local-safe defaults**
   - Replace hardcoded wildcard CORS in `src/main.py` with settings-driven config.
   - Keep permissive local default; allow stricter allowlists for future deployments.

2. **Refactor note async embedding tasks to use safe task boundaries**
   - Stop passing request `Session` and ORM objects in `note_service` background jobs.
   - Pass primitive inputs (note_id, tags snapshot), open fresh DB session in task.

3. **Refactor admin async tasks to use fresh DB sessions**
   - Update `/api/admin/reembed` and `/api/admin/sync-embeddings` task dispatch.
   - Ensure task execution does not depend on request lifecycle state.

4. **Add durable sync-state persistence for SQL↔Qdrant workflows**
   - Introduce migration/model fields (or table) for `last_sync_error`, `sync_attempts`, `last_sync_at`.
   - Expose this state through admin stats/config endpoints where useful.

5. **Implement retry/backoff for embedding and vector upsert failures**
   - Add bounded retries for transient provider/Qdrant failures.
   - Persist failures in sync-state fields without silent loss.

6. **Harden delete/update consistency paths with idempotent repair semantics**
   - Ensure stale vector edge cases are recoverable and visible.
   - Make sync-repair job safe to rerun repeatedly.

7. **Replace broad exception swallowing with structured error handling**
   - Remove print-based failures in services.
   - Use targeted exception classes and structured logs in search/admin/note services.

8. **Add readiness endpoint and startup resilience**
   - Keep `/api/health` as liveness.
   - Add readiness checks for DB + Qdrant.
   - Add bounded startup retry/backoff for dependency initialization.

9. **Align schema validation with DB constraints and normalize tags**
   - Add title/tag length constraints in Pydantic schemas.
   - Deduplicate/normalize tags before persistence.
   - Map `IntegrityError` to 409/422 instead of 500.

10. **Add admin + async reliability test coverage**
   - Add tests for `/api/admin/reembed` and `/api/admin/sync-embeddings`.
   - Add async embedding-mode tests for failure/retry and session safety.

11. **Resolve OpenAI provider strategy (keep legacy vs remove)**
   - If keeping: mark as legacy clearly in docs/config and avoid default usage.
   - If removing: delete provider path + dependency + docs references safely.

12. **Fix scripts/docs contract drift and add smoke verification target**
   - Align `scripts/seed.py` with actual API response contracts.
   - Remove README references to missing scripts or add equivalent scripts.
   - Add a lightweight smoke command in `Makefile` for script/docs contract checks.

13. **Finish uv-only dependency workflow cleanup**
   - Remove remaining non-doc references expecting `requirements.txt`.
   - Ensure Docker + local dev paths consistently use `uv sync` / `uv lock`.
