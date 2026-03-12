from enum import Enum


class SearchType(str, Enum):
    semantic = "semantic"
    keyword = "keyword"
    hybrid = "hybrid"
    graph = "graph"


class EmbeddingProvider(str, Enum):
    openai = "openai"
    ollama = "ollama"
