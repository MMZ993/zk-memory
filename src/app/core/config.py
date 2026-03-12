from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "AI Agent Memory System"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = ""

    # Database
    database_url: str = "sqlite:///./data/memory.db"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "notes_embeddings"
    qdrant_api_key: str = ""

    # Embeddings
    # Provider: "ollama" (default, local) | "openai" (cloud, requires API key)
    # Ollama model: nomic-embed-text (768-dim, fast, production-ready for home lab)
    #   Alternative: mxbai-embed-large (1024-dim, higher quality, more VRAM)
    # OpenAI model: text-embedding-ada-002 (1536-dim) — not used by default
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768
    embedding_mode: str = "sync"  # sync | async
    ollama_host: str = "http://localhost:11434"
    openai_api_key: str = ""  # only needed if embedding_provider=openai

    # Buffer
    buffer_retention_days: int = 7

    # Markdown export
    markdown_dir: str = "./data/notes"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
