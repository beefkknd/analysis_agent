"""Vector database service abstraction."""

from typing import Protocol, Any, TYPE_CHECKING
from config.settings import Settings

if TYPE_CHECKING:
    from services.embedding_service import EmbeddingService


class VectorDBService(Protocol):
    """
    Interface for vector database operations.

    Implementations should provide similarity search and upsert operations.
    """

    def query(
        self,
        query_text: str,
        collection: str,
        filter_dict: dict | None = None,
        limit: int = 3,
    ) -> list[dict]:
        """
        High-level query API - internally calculates embedding.

        Args:
            query_text: Text to search for
            collection: Collection/index name
            filter_dict: Optional metadata filter
            limit: Max number of results (default 3 for field mapping)

        Returns:
            List of matching documents with metadata
        """
        ...

    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 5,
        filter_dict: dict | None = None,
    ) -> list[dict]:
        """
        Low-level similarity search with pre-computed embedding.

        Args:
            collection: Collection/index name
            query_vector: Query embedding
            limit: Max number of results
            filter_dict: Optional metadata filter

        Returns:
            List of matching documents with metadata
        """
        ...

    def upsert(
        self,
        collection: str,
        vectors: list[list[float]],
        metadata: list[dict],
        texts: list[str] | None = None,
    ) -> None:
        """
        Insert or update vectors with metadata.

        Args:
            collection: Collection/index name
            vectors: List of embedding vectors
            metadata: List of metadata dicts (one per vector)
            texts: Optional list of original texts
        """
        ...


class ChromaDBService:
    """ChromaDB implementation of VectorDBService."""

    def __init__(self, settings: Settings, embedding_service: "EmbeddingService | None" = None):
        self.settings = settings
        self.embedding_service = embedding_service
        self.client = self._init_client()

    def _init_client(self):
        """Initialize ChromaDB client."""
        import chromadb
        return chromadb.PersistentClient(path=self.settings.chroma_persist_dir)

    def query(
        self,
        query_text: str,
        collection: str,
        filter_dict: dict | None = None,
        limit: int = 3,
    ) -> list[dict]:
        """High-level query - calculates embedding internally."""
        if not self.embedding_service:
            raise ValueError("EmbeddingService required for query() method")

        # Calculate embedding
        query_vector = self.embedding_service.embed_text(query_text)

        # Use search
        return self.search(collection, query_vector, limit, filter_dict)

    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 5,
        filter_dict: dict | None = None,
    ) -> list[dict]:
        """Similarity search in ChromaDB."""
        coll = self.client.get_or_create_collection(name=collection)

        # Build query params
        query_params = {
            "query_embeddings": [query_vector],
            "n_results": limit,
        }
        if filter_dict:
            query_params["where"] = filter_dict

        results = coll.query(**query_params)

        # Format results
        formatted = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                formatted.append({
                    'id': doc_id,
                    'text': results['documents'][0][i] if results.get('documents') else None,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else None,
                })

        return formatted

    def upsert(
        self,
        collection: str,
        vectors: list[list[float]],
        metadata: list[dict],
        texts: list[str] | None = None,
    ) -> None:
        """Insert/update vectors in ChromaDB."""
        coll = self.client.get_or_create_collection(name=collection)
        ids = [f"doc_{i}_{metadata[i].get('turn_id', i)}" for i in range(len(vectors))]

        upsert_params = {
            "embeddings": vectors,
            "metadatas": metadata,
            "ids": ids,
        }
        if texts:
            upsert_params["documents"] = texts

        coll.upsert(**upsert_params)


class RedisVectorService:
    """
    Redis implementation of VectorDBService (mock for now).

    Data structure pattern: text_to_embedding:blah -> payload:{...}
    """

    def __init__(self, settings: Settings, embedding_service: "EmbeddingService | None" = None):
        self.settings = settings
        self.embedding_service = embedding_service
        # Mock in-memory storage for now
        # In real implementation: import redis; self.client = redis.from_url(settings.redis_url)
        self._mock_storage: dict[str, list[dict]] = {}

    def query(
        self,
        query_text: str,
        collection: str,
        filter_dict: dict | None = None,
        limit: int = 3,
    ) -> list[dict]:
        """High-level query - calculates embedding internally."""
        if not self.embedding_service:
            raise ValueError("EmbeddingService required for query() method")

        # Calculate embedding
        query_vector = self.embedding_service.embed_text(query_text)

        # Use search
        return self.search(collection, query_vector, limit, filter_dict)

    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 5,
        filter_dict: dict | None = None,
    ) -> list[dict]:
        """
        Similarity search in Redis (mock).

        Real implementation would use Redis vector search commands.
        """
        # Mock: return stored items (in real impl, do cosine similarity search)
        items = self._mock_storage.get(collection, [])

        # Apply filter if provided
        if filter_dict:
            items = [item for item in items if self._matches_filter(item['metadata'], filter_dict)]

        # Mock similarity scoring (just return first N)
        results = items[:limit]

        return results

    def upsert(
        self,
        collection: str,
        vectors: list[list[float]],
        metadata: list[dict],
        texts: list[str] | None = None,
    ) -> None:
        """
        Insert/update vectors in Redis (mock).

        Data pattern: text_to_embedding:{collection}:{id} -> payload
        """
        if collection not in self._mock_storage:
            self._mock_storage[collection] = []

        for i, vector in enumerate(vectors):
            item = {
                'id': f"{collection}:{i}",
                'embedding': vector,
                'metadata': metadata[i],
                'text': texts[i] if texts and i < len(texts) else None,
            }
            self._mock_storage[collection].append(item)

    def _matches_filter(self, metadata: dict, filter_dict: dict) -> bool:
        """Check if metadata matches filter."""
        for key, value in filter_dict.items():
            if metadata.get(key) != value:
                return False
        return True


def create_vectordb_service(
    settings: Settings,
    embedding_service: "EmbeddingService | None" = None
) -> VectorDBService:
    """
    Factory function to create appropriate vector DB service.

    Args:
        settings: Application settings
        embedding_service: Optional embedding service for high-level query() API
    """
    if settings.vector_db_type == "chroma":
        return ChromaDBService(settings, embedding_service)
    elif settings.vector_db_type == "redis":
        return RedisVectorService(settings, embedding_service)
    else:
        raise ValueError(f"Unsupported vector DB type: {settings.vector_db_type}")
