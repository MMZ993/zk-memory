from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import get_settings

settings = get_settings()

client = QdrantClient(
    host=settings.qdrant_host,
    port=settings.qdrant_port,
    api_key=settings.qdrant_api_key or None,
)

QDRANT_COLLECTION = settings.qdrant_collection


def init_qdrant():
    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
