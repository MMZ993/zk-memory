# Session Plan — 2026-03-31

## Goal
Fix Docker integration test startup contract drift so all integration test targets run successfully again.

## Tasks
- [x] Update integration Docker compose commands to match image runtime (`uv run uvicorn ...`) for sqlite/postgres/auth stacks (td:td-525e18)
- [x] Run all integration make targets and confirm end-to-end startup/test execution path is healthy (td:td-525e18)
- [x] Verify docs/scripts references for integration commands remain accurate after compose fixes (td:td-525e18)

## Notes
- Reprioritized after verification findings: all integration compose targets fail with `exec: "uvicorn": executable file not found in $PATH`.
- `td-525e18` is now `in_progress`; `td-9c0794` moved back to `open` and remains next reliability item after this fix.
