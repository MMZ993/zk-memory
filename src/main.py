import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import init_db
from app.db.qdrant import init_qdrant

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Agent Memory System")
    init_db()
    init_qdrant()
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


@app.get("/")
async def root():
    return {
        "message": "AI Agent Memory System API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
