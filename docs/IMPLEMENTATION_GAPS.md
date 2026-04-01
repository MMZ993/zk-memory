# Implementation Gaps

## Resolved

- ~~Route naming: `GET /api/notes/get/{id}` non-RESTful~~ → Fixed: `GET /api/notes/{id}`, search registered before /{id}
- ~~`DELETE /api/buffer/processed` query param~~ → Fixed: `DELETE /api/buffer/cleanup` reads `BUFFER_RETENTION_DAYS` from env (0 = disabled)
- ~~Re-embed status has no backing store~~ → Fixed: stored in `metadata` table as `reembed_status` key (idle/in_progress/finished)
- ~~Keyword search described as fuzzy but used LIKE~~ → Fixed: uses SQLite FTS5
- ~~`color` field on RelationType implies UI that doesn't exist~~ → Removed
- ~~Two embedding files: `utils/embeddings.py` + `services/embedding_service.py`~~ → Use only `services/embedding_service.py`
- ~~Backup API endpoints not implementable cleanly~~ → Removed; backup is external (file copy). See `docs/backup-strategy.md`
- ~~`synced` semantics unclear~~ → Documented: `false` = not yet embedded; `true` = Qdrant vector is current
- ~~Add-tag requires UUID but create-note accepts names~~ → Fixed: `POST /api/notes/{id}/tags` accepts `{"name": "string"}` and auto-creates
- ~~No `updated_at`/`processed_at` on buffer notes~~ → Added both columns
- ~~Duplicate buffer export endpoint~~ → Removed `GET /api/buffer/export`; canonical is `GET /api/export/buffer`

## Open / Future

- No rate limiting or request body size limits — relevant if exposing over network
- ~~Package version pins are from late 2023~~ → Updated to match installed versions (2026-03-12)
- Bash scripts deferred to Phase 9 (optional)

## Dependency Compatibility Notes (for coding phases)

### Local embedding provider
- Embeddings are local-only via Ollama.
- Keep `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, and `OLLAMA_HOST` aligned.

### pytest-asyncio 1.x (installed: 1.3.0, was pinned at >=0.21.0)
- `asyncio_mode = "auto"` is now set in `pyproject.toml` under `[tool.pytest.ini_options]` — already added
- In v1.x, the `@pytest.mark.asyncio` decorator is no longer required on individual tests (auto mode handles it)
- `pytest.fixture` async fixtures work without `@pytest_asyncio.fixture` in auto mode
- **Breaking**: `event_loop` fixture scope changed — don't override `event_loop` fixture; use `anyio` backend or accept per-test loops
- When writing tests: just `async def test_foo():` works without any decorator
