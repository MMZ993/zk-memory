"""
Integration test configuration — real running API via Docker.

Run with:
    INTEGRATION_TESTS=1 pytest tests/integration/ -v

The test stack must be running before executing tests:
    docker compose -f docker-compose.test.yml up -d --build
    INTEGRATION_TESTS=1 pytest tests/integration/ -v
    docker compose -f docker-compose.test.yml down -v

Or use the Makefile shortcut:
    make test-integration

Requires:
    - docker-compose.test.yml stack running (agents-memory-test + qdrant-test)
    - Ollama with nomic-embed-text running on the host (port 11434)

Configuration (env vars):
    MEMORY_API_URL   API base URL          (default: http://localhost:8001)
    INTEGRATION_TESTS=1  required to enable tests
"""

import os
import time

import httpx
import pytest

API_URL = os.getenv("MEMORY_API_URL", "http://localhost:8001")


# ── Guard: skip entire directory unless INTEGRATION_TESTS=1 ──────────────────

def pytest_collection_modifyitems(config, items):
    if os.getenv("INTEGRATION_TESTS"):
        return
    skip = pytest.mark.skip(reason="Set INTEGRATION_TESTS=1 to run integration tests")
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(skip)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wait_for_api(url: str, timeout: int = 60) -> None:
    """Poll /health until the API is ready or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{url}/health", timeout=5)
            if r.status_code == 200:
                return
        except httpx.ConnectError:
            pass
        time.sleep(2)
    pytest.skip(f"API at {url} did not become ready within {timeout}s — is the test stack running?")


def _wipe_data(client: httpx.Client) -> None:
    """Delete all notes and buffer notes before seeding a fresh dataset.

    Deleting notes via the API removes them from both SQLite and Qdrant
    (note_service.delete_note handles both stores).
    """
    resp = client.get("/api/notes/", params={"limit": 500})
    if resp.status_code == 200:
        for note in resp.json():
            client.delete(f"/api/notes/{note['id']}")

    resp = client.get("/api/buffer/", params={"limit": 500})
    if resp.status_code == 200:
        for note in resp.json():
            client.delete(f"/api/buffer/{note['id']}")


# ── Session-scoped seeded client ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def seeded_client():
    """
    One-time setup for the whole integration test session:

    1. Wait for the API to respond on MEMORY_API_URL.
    2. Wipe all existing notes + buffer (clean slate).
    3. Seed 14 smart-home notes + 13 links via the real HTTP API.
    4. Yield (client, note_ids) to all tests.
    """
    _wait_for_api(API_URL)

    client = httpx.Client(base_url=API_URL, timeout=60.0)

    _wipe_data(client)

    from tests.integration.fixtures import seed_data
    note_ids = seed_data(client)

    yield client, note_ids

    client.close()


# ── Convenience aliases used by test modules ──────────────────────────────────

@pytest.fixture(scope="session")
def client(seeded_client):
    c, _ = seeded_client
    return c


@pytest.fixture(scope="session")
def note_ids(seeded_client):
    _, ids = seeded_client
    return ids
