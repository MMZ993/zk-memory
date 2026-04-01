import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from qdrant_client.http.exceptions import ApiException, ResponseHandlingException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.db import qdrant as qdrant_db
from app.db.session import init_db
from app.db.qdrant import init_qdrant

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)
_STARTUP_MAX_ATTEMPTS = 3
_STARTUP_BACKOFF_SECONDS = 0.5
_QDRANT_RETRYABLE_ERRORS = (
    ConnectionError,
    TimeoutError,
    httpx.HTTPError,
    ApiException,
    ResponseHandlingException,
)
_DB_RETRYABLE_ERRORS = (SQLAlchemyError, ConnectionError, TimeoutError)


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


@app.get("/")
async def root():
    return {
        "message": "AI Agent Memory System API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
