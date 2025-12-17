"""Embedding service abstraction."""

from langchain_openai import OpenAIEmbeddings
from config.settings import Settings


class EmbeddingService:
    """
    Embedding generation abstraction.

    Supports OpenAI embeddings and local models.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.embeddings = self._init_embeddings()

    def _init_embeddings(self):
        """Initialize embedding client based on settings."""
        if self.settings.embedding_provider == "openai":
            return OpenAIEmbeddings(
                model=self.settings.embedding_model,
                api_key=self.settings.openai_api_key,
            )
        elif self.settings.embedding_provider == "local":
            # TODO: Implement local embeddings (e.g., sentence-transformers)
            raise NotImplementedError("Local embeddings not yet implemented")
        else:
            raise ValueError(f"Unsupported embedding provider: {self.settings.embedding_provider}")

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        return self.embeddings.embed_query(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return self.embeddings.embed_documents(texts)
