import importlib
import io
import json
import logging
import sys

import pytest


def _string_values(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values = []
        for key, nested_value in value.items():
            values.extend(_string_values(key))
            values.extend(_string_values(nested_value))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for nested_value in value:
            values.extend(_string_values(nested_value))
        return values
    return []


def test_request_logging_records_safe_response_metadata(client, caplog):
    caplog.set_level(logging.INFO, logger="main")

    response = client.get(
        "/api/health?token=secret",
        headers={"X-API-Key": "secret-key", "Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    completion_logs = [
        record
        for record in caplog.records
        if record.name == "main" and record.message == "HTTP request completed"
    ]
    assert completion_logs
    record = completion_logs[-1]
    assert record.method == "GET"
    assert record.path == "/api/health"
    assert record.status_code == 200
    assert record.duration_ms >= 0
    logged_values = []
    for value in record.__dict__.values():
        logged_values.extend(_string_values(value))
    assert not any("secret" in value for value in logged_values)


def test_json_log_format_outputs_structured_request_fields(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_FORMAT", "json")

    from app.core.config import get_settings
    import main as main_module

    get_settings.cache_clear()
    reloaded_main = importlib.reload(main_module)

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(reloaded_main._build_log_formatter())

    record = logging.LogRecord(
        name="main",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="HTTP request completed",
        args=(),
        exc_info=None,
    )
    record.method = "GET"
    record.path = "/api/health"
    record.status_code = 200
    record.duration_ms = 1.5

    handler.handle(record)

    payload = json.loads(stream.getvalue())
    assert payload == {
        "level": "INFO",
        "logger": "main",
        "message": "HTTP request completed",
        "method": "GET",
        "path": "/api/health",
        "status_code": 200,
        "duration_ms": 1.5,
    }


def test_json_log_format_excludes_unsafe_extra_fields(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_FORMAT", "json")

    from app.core.config import get_settings
    import main as main_module

    get_settings.cache_clear()
    reloaded_main = importlib.reload(main_module)

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(reloaded_main._build_log_formatter())

    record = logging.LogRecord(
        name="main",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Startup dependency initialization failed",
        args=(),
        exc_info=None,
    )
    record.error = "secret database connection failure"
    record.headers = {"Authorization": "Bearer secret-token"}
    record.token = "secret-token"

    handler.handle(record)

    payload = json.loads(stream.getvalue())
    assert "secret" not in json.dumps(payload)


def test_json_log_format_preserves_exception_details(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_FORMAT", "json")

    from app.core.config import get_settings
    import main as main_module

    get_settings.cache_clear()
    reloaded_main = importlib.reload(main_module)

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(reloaded_main._build_log_formatter())

    try:
        raise RuntimeError("expected exception detail")
    except RuntimeError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="app.services.example",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Service failed",
        args=(),
        exc_info=exc_info,
    )

    handler.handle(record)

    payload = json.loads(stream.getvalue())
    assert "RuntimeError: expected exception detail" in payload["exception"]


def test_request_logging_records_cors_preflight_responses(client, caplog):
    caplog.set_level(logging.INFO, logger="main")

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    completion_logs = [
        record
        for record in caplog.records
        if record.name == "main" and record.message == "HTTP request completed"
    ]
    assert completion_logs[-1].method == "OPTIONS"


def test_request_logging_records_error_response_status(client, caplog):
    caplog.set_level(logging.INFO, logger="main")

    response = client.get("/api/missing")

    assert response.status_code == 404
    completion_logs = [
        record
        for record in caplog.records
        if record.name == "main" and record.message == "HTTP request completed"
    ]
    assert completion_logs[-1].status_code == 404


def test_request_logging_records_unhandled_exception(client, caplog):
    async def crashing_endpoint():
        raise RuntimeError("request logging test failure")

    client.app.add_api_route(
        "/api/request-logging-test-failure",
        crashing_endpoint,
        methods=["GET"],
    )
    caplog.set_level(logging.ERROR, logger="main")

    with pytest.raises(RuntimeError, match="request logging test failure"):
        client.get("/api/request-logging-test-failure")

    failure_logs = [
        record
        for record in caplog.records
        if record.name == "main" and record.message == "HTTP request failed"
    ]
    assert failure_logs[-1].status_code == 500
