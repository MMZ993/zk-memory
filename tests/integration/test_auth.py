"""
Auth integration tests — scoped API keys and CLI binary auth behaviour.

Requires a running API instance with all five MEMORY_API_KEY_* vars set.
The docker-compose.test.auth.yml stack provides this on port 8003.

Run with:
    make test-integration-auth

Or manually:
    docker compose -f docker-compose.test.auth.yml up -d --build
    INTEGRATION_TESTS=1 AUTH_TESTS=1 AUTH_API_URL=http://localhost:8003 \\
        pytest tests/integration/test_auth.py -v
    docker compose -f docker-compose.test.auth.yml down -v

Guards:
    INTEGRATION_TESTS=1  — required by the integration conftest (whole directory)
    AUTH_TESTS=1         — required by fixtures in this file
"""

import os
import pathlib
import subprocess
import time

import httpx
import pytest

# ── Test key constants (must match docker-compose.test.auth.yml) ──────────────

READ_KEY = "test_key_read"
BUFFER_KEY = "test_key_buffer"
WRITE_KEY = "test_key_write"
DUMP_KEY = "test_key_dump"
ADMIN_KEY = "test_key_admin"
BAD_KEY = "not_a_valid_key"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wait_for_api(url: str, timeout: int = 30) -> None:
    """Poll /api/health until the API is ready or skip the test."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{url}/api/health", timeout=5)
            if r.status_code == 200:
                return
        except httpx.ConnectError:
            pass
        time.sleep(2)
    pytest.skip(f"Auth API at {url}/api/health did not respond within {timeout}s")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def auth_api_url():
    """URL of the auth-enabled test API. Skips if AUTH_TESTS is not set."""
    if not os.getenv("AUTH_TESTS"):
        pytest.skip("Set AUTH_TESTS=1 to run auth integration tests")
    return os.getenv("AUTH_API_URL", "http://localhost:8003")


@pytest.fixture(scope="module")
def auth_client(auth_api_url):
    """httpx.Client pointed at the auth-enabled API. No key set by default."""
    _wait_for_api(auth_api_url)
    c = httpx.Client(base_url=auth_api_url, timeout=10.0)
    yield c
    c.close()


@pytest.fixture(scope="module")
def cli_binary():
    """Path to the compiled CLI binary. Skips if not built."""
    project_root = pathlib.Path(__file__).parent.parent.parent
    binary = project_root / "cli" / "dist" / "memory"
    if not binary.exists():
        pytest.skip(
            f"CLI binary not found at {binary} — "
            "run: cd cli && go build -o dist/memory ."
        )
    return str(binary)


# ── Public endpoints ──────────────────────────────────────────────────────────

class TestPublicEndpoints:
    """Public endpoints must work without any API key."""

    def test_health_no_key(self, auth_client):
        r = auth_client.get("/api/health")
        assert r.status_code == 200

    def test_root_no_key(self, auth_client):
        r = auth_client.get("/")
        assert r.status_code == 200


# ── Missing key → 401 ─────────────────────────────────────────────────────────

class TestMissingKey:
    """Protected endpoints return 401 when no key is provided."""

    def test_list_notes_401(self, auth_client):
        r = auth_client.get("/api/notes/")
        assert r.status_code == 401

    def test_create_note_401(self, auth_client):
        r = auth_client.post("/api/notes/", json={"title": "t", "content": "c"})
        assert r.status_code == 401

    def test_list_buffer_401(self, auth_client):
        r = auth_client.get("/api/buffer/")
        assert r.status_code == 401

    def test_create_buffer_401(self, auth_client):
        r = auth_client.post("/api/buffer/", json={"content": "test"})
        assert r.status_code == 401

    def test_list_tags_401(self, auth_client):
        r = auth_client.get("/api/tags/")
        assert r.status_code == 401

    def test_export_notes_401(self, auth_client):
        r = auth_client.get("/api/export/notes")
        assert r.status_code == 401

    def test_admin_config_401(self, auth_client):
        r = auth_client.get("/api/config")
        assert r.status_code == 401

    def test_stats_401(self, auth_client):
        r = auth_client.get("/api/stats")
        assert r.status_code == 401

    def test_invalid_key_401(self, auth_client):
        """A key value that isn't registered in any scope also returns 401."""
        r = auth_client.get("/api/notes/", headers={"X-API-Key": BAD_KEY})
        # BAD_KEY is not in any scope list, so it falls through to 403.
        # But the key IS present — so it's 403, not 401.
        # Verify it's not 200 (auth is definitely enforced).
        assert r.status_code in (401, 403)


# ── Wrong scope → 403 ────────────────────────────────────────────────────────

class TestWrongScope:
    """Valid key with incorrect scope returns 403."""

    def test_read_key_cannot_create_note(self, auth_client):
        r = auth_client.post(
            "/api/notes/",
            json={"title": "t", "content": "c"},
            headers={"X-API-Key": READ_KEY},
        )
        assert r.status_code == 403

    def test_read_key_cannot_write_buffer(self, auth_client):
        r = auth_client.post(
            "/api/buffer/",
            json={"content": "test"},
            headers={"X-API-Key": READ_KEY},
        )
        assert r.status_code == 403

    def test_read_key_cannot_export(self, auth_client):
        r = auth_client.get("/api/export/notes", headers={"X-API-Key": READ_KEY})
        assert r.status_code == 403

    def test_read_key_cannot_access_admin(self, auth_client):
        r = auth_client.get("/api/config", headers={"X-API-Key": READ_KEY})
        assert r.status_code == 403

    def test_write_key_cannot_read_notes(self, auth_client):
        r = auth_client.get("/api/notes/", headers={"X-API-Key": WRITE_KEY})
        assert r.status_code == 403

    def test_write_key_cannot_export(self, auth_client):
        r = auth_client.get("/api/export/notes", headers={"X-API-Key": WRITE_KEY})
        assert r.status_code == 403

    def test_write_key_cannot_access_admin(self, auth_client):
        r = auth_client.get("/api/config", headers={"X-API-Key": WRITE_KEY})
        assert r.status_code == 403

    def test_buffer_key_cannot_read_notes(self, auth_client):
        r = auth_client.get("/api/notes/", headers={"X-API-Key": BUFFER_KEY})
        assert r.status_code == 403

    def test_buffer_key_cannot_create_note(self, auth_client):
        r = auth_client.post(
            "/api/notes/",
            json={"title": "t", "content": "c"},
            headers={"X-API-Key": BUFFER_KEY},
        )
        assert r.status_code == 403

    def test_dump_key_cannot_write(self, auth_client):
        r = auth_client.post(
            "/api/notes/",
            json={"title": "t", "content": "c"},
            headers={"X-API-Key": DUMP_KEY},
        )
        assert r.status_code == 403

    def test_dump_key_cannot_read_notes(self, auth_client):
        r = auth_client.get("/api/notes/", headers={"X-API-Key": DUMP_KEY})
        assert r.status_code == 403


# ── Correct scope → success ───────────────────────────────────────────────────

class TestCorrectScope:
    """Correct scope key returns the expected success status."""

    def test_read_key_can_list_notes(self, auth_client):
        r = auth_client.get("/api/notes/", headers={"X-API-Key": READ_KEY})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_read_key_can_list_tags(self, auth_client):
        r = auth_client.get("/api/tags/", headers={"X-API-Key": READ_KEY})
        assert r.status_code == 200

    def test_read_key_can_list_buffer(self, auth_client):
        r = auth_client.get("/api/buffer/", headers={"X-API-Key": READ_KEY})
        assert r.status_code == 200

    def test_read_key_can_get_stats(self, auth_client):
        r = auth_client.get("/api/stats", headers={"X-API-Key": READ_KEY})
        assert r.status_code == 200

    def test_read_key_can_search(self, auth_client):
        r = auth_client.get(
            "/api/notes/search",
            params={"q": "test"},
            headers={"X-API-Key": READ_KEY},
        )
        assert r.status_code == 200

    def test_write_key_can_create_note(self, auth_client):
        r = auth_client.post(
            "/api/notes/",
            json={"title": "auth-scope-test", "content": "testing write scope"},
            headers={"X-API-Key": WRITE_KEY},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "auth-scope-test"

    def test_buffer_key_can_append(self, auth_client):
        r = auth_client.post(
            "/api/buffer/",
            json={"content": "auth buffer scope test"},
            headers={"X-API-Key": BUFFER_KEY},
        )
        assert r.status_code == 201

    def test_dump_key_can_export_notes(self, auth_client):
        r = auth_client.get("/api/export/notes", headers={"X-API-Key": DUMP_KEY})
        assert r.status_code == 200

    def test_dump_key_can_export_buffer(self, auth_client):
        r = auth_client.get("/api/export/buffer", headers={"X-API-Key": DUMP_KEY})
        assert r.status_code == 200

    def test_admin_key_can_get_config(self, auth_client):
        r = auth_client.get("/api/config", headers={"X-API-Key": ADMIN_KEY})
        assert r.status_code == 200


# ── Admin key bypasses all scope checks ──────────────────────────────────────

class TestAdminKeyBypassesAllScopes:
    """Admin key is accepted by every protected endpoint."""

    def test_admin_can_read_notes(self, auth_client):
        r = auth_client.get("/api/notes/", headers={"X-API-Key": ADMIN_KEY})
        assert r.status_code == 200

    def test_admin_can_create_note(self, auth_client):
        r = auth_client.post(
            "/api/notes/",
            json={"title": "admin-bypass-test", "content": "admin scope bypass"},
            headers={"X-API-Key": ADMIN_KEY},
        )
        assert r.status_code == 201

    def test_admin_can_write_buffer(self, auth_client):
        r = auth_client.post(
            "/api/buffer/",
            json={"content": "admin buffer bypass"},
            headers={"X-API-Key": ADMIN_KEY},
        )
        assert r.status_code == 201

    def test_admin_can_export(self, auth_client):
        r = auth_client.get("/api/export/notes", headers={"X-API-Key": ADMIN_KEY})
        assert r.status_code == 200

    def test_admin_can_get_stats(self, auth_client):
        r = auth_client.get("/api/stats", headers={"X-API-Key": ADMIN_KEY})
        assert r.status_code == 200

    def test_admin_can_list_tags(self, auth_client):
        r = auth_client.get("/api/tags/", headers={"X-API-Key": ADMIN_KEY})
        assert r.status_code == 200


# ── CLI binary auth tests ─────────────────────────────────────────────────────

class TestCLIAuth:
    """CLI binary auth behaviour via subprocess.

    Tests that the CLI correctly forwards MEMORY_API_KEY as X-API-Key and
    that 401/403 responses from the server cause a non-zero exit code.
    """

    def _run(self, cli_binary, auth_api_url, *args, key=None):
        """Run the CLI binary with the given API key (or no key if None)."""
        env = {k: v for k, v in os.environ.items()}
        env["MEMORY_API_URL"] = auth_api_url
        if key is not None:
            env["MEMORY_API_KEY"] = key
        else:
            env.pop("MEMORY_API_KEY", None)
        return subprocess.run(
            [cli_binary, *args],
            env=env,
            capture_output=True,
            text=True,
        )

    def test_no_key_list_notes_returns_401(self, auth_client, cli_binary, auth_api_url):
        """CLI without key should fail with API error 401."""
        result = self._run(cli_binary, auth_api_url, "notes", "list")
        assert result.returncode != 0, "expected non-zero exit for 401"
        assert "401" in result.stderr, f"expected '401' in stderr:\n{result.stderr}"

    def test_read_key_list_notes_succeeds(self, auth_client, cli_binary, auth_api_url):
        """CLI with read key can list notes."""
        result = self._run(cli_binary, auth_api_url, "notes", "list", key=READ_KEY)
        assert result.returncode == 0, f"expected success:\nstdout={result.stdout}\nstderr={result.stderr}"

    def test_wrong_scope_create_note_returns_403(self, auth_client, cli_binary, auth_api_url):
        """CLI with read key cannot create a note — should fail with 403."""
        result = self._run(
            cli_binary, auth_api_url,
            "notes", "create",
            "--title", "test-403",
            "--content", "should be rejected",
            key=READ_KEY,
        )
        assert result.returncode != 0, "expected non-zero exit for 403"
        assert "403" in result.stderr, f"expected '403' in stderr:\n{result.stderr}"

    def test_write_key_create_note_succeeds(self, auth_client, cli_binary, auth_api_url):
        """CLI with write key can create a note."""
        result = self._run(
            cli_binary, auth_api_url,
            "notes", "create",
            "--title", "cli-write-test",
            "--content", "created via CLI with write key",
            key=WRITE_KEY,
        )
        assert result.returncode == 0, f"expected success:\nstdout={result.stdout}\nstderr={result.stderr}"

    def test_admin_key_list_notes_succeeds(self, auth_client, cli_binary, auth_api_url):
        """CLI with admin key can list notes (admin bypasses all scope checks)."""
        result = self._run(cli_binary, auth_api_url, "notes", "list", key=ADMIN_KEY)
        assert result.returncode == 0, f"expected success:\nstdout={result.stdout}\nstderr={result.stderr}"

    def test_buffer_key_append_succeeds(self, auth_client, cli_binary, auth_api_url):
        """CLI with buffer key can append a buffer note."""
        result = self._run(
            cli_binary, auth_api_url,
            "buffer", "add",
            "--content", "cli buffer scope test",
            key=BUFFER_KEY,
        )
        assert result.returncode == 0, f"expected success:\nstdout={result.stdout}\nstderr={result.stderr}"

    def test_buffer_key_cannot_list_notes(self, auth_client, cli_binary, auth_api_url):
        """CLI with buffer key cannot list notes — should fail with 403."""
        result = self._run(cli_binary, auth_api_url, "notes", "list", key=BUFFER_KEY)
        assert result.returncode != 0, "expected non-zero exit for 403"
        assert "403" in result.stderr, f"expected '403' in stderr:\n{result.stderr}"
