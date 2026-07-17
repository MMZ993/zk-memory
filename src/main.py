import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from qdrant_client.http.exceptions import ApiException, ResponseHandlingException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.db import qdrant as qdrant_db
from app.db.session import init_db
from app.db.qdrant import init_qdrant
from app.metrics import METRICS_CONTENT_TYPE, record_http_request, render_metrics

_STARTUP_MAX_ATTEMPTS = 3
_STARTUP_BACKOFF_SECONDS = 0.5
_JSON_LOG_EXTRA_FIELDS = frozenset(
    {
        "attempt",
        "client_host",
        "dependency",
        "duration_ms",
        "max_attempts",
        "method",
        "path",
        "retry_delay_seconds",
        "status_code",
    }
)
_QDRANT_RETRYABLE_ERRORS = (
    ConnectionError,
    TimeoutError,
    httpx.HTTPError,
    ApiException,
    ResponseHandlingException,
)
_DB_RETRYABLE_ERRORS = (SQLAlchemyError, ConnectionError, TimeoutError)
_METRIC_HTTP_METHODS = frozenset(
    {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _JSON_LOG_EXTRA_FIELDS and value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _build_log_formatter() -> logging.Formatter:
    if settings.log_format.lower() == "json":
        return JsonLogFormatter()
    return logging.Formatter("%(levelname)s:%(name)s:%(message)s")


settings = get_settings()
root_logger = logging.getLogger()
log_level = getattr(logging, settings.log_level)
if not root_logger.handlers:
    root_logger.setLevel(log_level)
    handler = logging.StreamHandler()
    handler.setFormatter(_build_log_formatter())
    root_logger.addHandler(handler)
else:
    for handler in root_logger.handlers:
        if handler.formatter is None:
            handler.setFormatter(_build_log_formatter())
logger = logging.getLogger(__name__)
logger.setLevel(log_level)


async def _run_startup_with_retry(init_name: str, init_fn, retryable_errors):
    for attempt in range(1, _STARTUP_MAX_ATTEMPTS + 1):
        try:
            init_fn()
            return
        except retryable_errors as exc:
            if attempt == _STARTUP_MAX_ATTEMPTS:
                logger.error(
                    "Startup dependency initialization failed permanently",
                    extra={
                        "dependency": init_name,
                        "attempt": attempt,
                        "max_attempts": _STARTUP_MAX_ATTEMPTS,
                        "error": str(exc),
                    },
                )
                raise

            logger.warning(
                "Startup dependency initialization failed; retrying",
                extra={
                    "dependency": init_name,
                    "attempt": attempt,
                    "max_attempts": _STARTUP_MAX_ATTEMPTS,
                    "error": str(exc),
                    "retry_delay_seconds": _STARTUP_BACKOFF_SECONDS * attempt,
                },
            )
            await asyncio.sleep(_STARTUP_BACKOFF_SECONDS * attempt)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Agent Memory System")
    await _run_startup_with_retry("database", init_db, _DB_RETRYABLE_ERRORS)
    await _run_startup_with_retry("qdrant", init_qdrant, _QDRANT_RETRYABLE_ERRORS)
    yield
    logger.info("Shutting down AI Agent Memory System")


app = FastAPI(
    title="AI Agent Memory System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    logger.info(
        "HTTP request started",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else None,
        },
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_seconds = time.perf_counter() - start_time
        duration_ms = round(duration_seconds * 1000, 2)
        path = _metric_route_path(request)
        record_http_request(_metric_http_method(request), path, 500, duration_seconds)
        logger.error(
            "HTTP request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
                "client_host": request.client.host if request.client else None,
            },
        )
        raise

    duration_seconds = time.perf_counter() - start_time
    duration_ms = round(duration_seconds * 1000, 2)
    path = _metric_route_path(request)
    record_http_request(
        _metric_http_method(request), path, response.status_code, duration_seconds
    )
    logger.info(
        "HTTP request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_host": request.client.host if request.client else None,
        },
    )
    return response


def _metric_route_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


def _metric_http_method(request: Request) -> str:
    return request.method if request.method in _METRIC_HTTP_METHODS else "OTHER"

from app.api import buffer, notes, tags, relations, export, admin  # noqa: E402

app.include_router(buffer.router)
app.include_router(notes.router)
app.include_router(tags.router)
app.include_router(relations.router)
app.include_router(export.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/readiness")
async def readiness_check(db: Session = Depends(get_db)):
    dependencies = {"database": "ok", "qdrant": "ok"}

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        dependencies["database"] = "error"

    try:
        collection_exists = qdrant_db.client.collection_exists(
            qdrant_db.QDRANT_COLLECTION
        )
        if not collection_exists:
            dependencies["qdrant"] = "error"
    except _QDRANT_RETRYABLE_ERRORS:
        dependencies["qdrant"] = "error"

    is_ready = all(status == "ok" for status in dependencies.values())
    payload = {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": dependencies,
    }
    if is_ready:
        return payload
    return JSONResponse(status_code=503, content=payload)


@app.get("/metrics", include_in_schema=False)
def metrics_endpoint(db: Session = Depends(get_db)):
    return Response(
        content=render_metrics(db),
        headers={"Content-Type": METRICS_CONTENT_TYPE},
    )


@app.get("/")
async def root():
    return {
        "message": "AI Agent Memory System API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
