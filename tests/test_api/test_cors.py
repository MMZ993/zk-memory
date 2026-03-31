import importlib

from fastapi.testclient import TestClient


_CORS_ENV_KEYS = (
    "CORS_ALLOW_ORIGINS",
    "CORS_ALLOW_ORIGIN_REGEX",
    "CORS_ALLOW_METHODS",
    "CORS_ALLOW_HEADERS",
)


def _reload_app_with_env(
    monkeypatch, env: dict[str, str], *, use_clean_env_file: bool = False, tmp_path=None
):
    if use_clean_env_file and tmp_path is not None:
        monkeypatch.chdir(tmp_path)

    for key in _CORS_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    from app.core.config import get_settings
    import main as main_module

    get_settings.cache_clear()
    importlib.reload(main_module)

    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "init_qdrant", lambda: None)
    return main_module.app


def test_cors_preflight_allows_local_origin_by_default(monkeypatch, tmp_path):
    app = _reload_app_with_env(
        monkeypatch,
        {},
        use_clean_env_file=True,
        tmp_path=tmp_path,
    )

    with TestClient(app) as client:
        r = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_preflight_rejects_non_local_origin_by_default(monkeypatch, tmp_path):
    app = _reload_app_with_env(
        monkeypatch,
        {},
        use_clean_env_file=True,
        tmp_path=tmp_path,
    )

    with TestClient(app) as client:
        r = client.options(
            "/api/health",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers


def test_cors_env_override_supports_comma_separated_origins(monkeypatch):
    app = _reload_app_with_env(
        monkeypatch,
        {
            "CORS_ALLOW_ORIGINS": "https://app.example,https://ui.local",
            "CORS_ALLOW_ORIGIN_REGEX": "",
            "CORS_ALLOW_METHODS": "*",
            "CORS_ALLOW_HEADERS": "*",
        },
    )

    with TestClient(app) as client:
        allowed = client.options(
            "/api/health",
            headers={
                "Origin": "https://app.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        second_allowed = client.options(
            "/api/health",
            headers={
                "Origin": "https://ui.local",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "https://app.example"
    assert second_allowed.status_code == 200
    assert (
        second_allowed.headers.get("access-control-allow-origin") == "https://ui.local"
    )


def test_cors_env_override_supports_json_origin_list(monkeypatch):
    app = _reload_app_with_env(
        monkeypatch,
        {
            "CORS_ALLOW_ORIGINS": '["https://app.example"]',
            "CORS_ALLOW_ORIGIN_REGEX": "",
            "CORS_ALLOW_METHODS": "*",
            "CORS_ALLOW_HEADERS": "*",
        },
    )

    with TestClient(app) as client:
        allowed = client.options(
            "/api/health",
            headers={
                "Origin": "https://app.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        blocked = client.options(
            "/api/health",
            headers={
                "Origin": "https://other.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "https://app.example"
    assert blocked.status_code == 400


def test_cors_env_override_applies_methods_and_headers(monkeypatch):
    app = _reload_app_with_env(
        monkeypatch,
        {
            "CORS_ALLOW_ORIGINS": "https://app.example",
            "CORS_ALLOW_ORIGIN_REGEX": "",
            "CORS_ALLOW_METHODS": "GET",
            "CORS_ALLOW_HEADERS": "X-Token",
        },
    )

    with TestClient(app) as client:
        allowed = client.options(
            "/api/health",
            headers={
                "Origin": "https://app.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Token",
            },
        )
        blocked_method = client.options(
            "/api/health",
            headers={
                "Origin": "https://app.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Token",
            },
        )
        blocked_header = client.options(
            "/api/health",
            headers={
                "Origin": "https://app.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Other",
            },
        )

    assert allowed.status_code == 200
    assert blocked_method.status_code == 400
    assert blocked_header.status_code == 400
