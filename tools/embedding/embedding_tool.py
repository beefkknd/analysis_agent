"""Embedding generation tool."""

from tools.base import BaseTool, ToolResult
from services.embedding_service import EmbeddingService


class EmbeddingTool(BaseTool):
    """
    Stateless embedding tool.
    Generates embeddings for text.
    """

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service

    @property
    def name(self) -> str:
        return "embedding"

    @property
    def description(self) -> str:
        return "Generate embeddings for text using configured model"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to embed"},
                "batch": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Batch of texts to embed (alternative to single text)"
                },
            },
            "oneOf": [
                {"required": ["text"]},
                {"required": ["batch"]}
            ]
        }

    def execute(
        self,
        text: str | None = None,
        batch: list[str] | None = None,
    ) -> ToolResult:
        """
        Generate embedding(s).

        Args:
            text: Single text to embed (or None for batch)
            batch: List of texts to embed (or None for single)
        """
        try:
            if text is not None:
                embedding = self.embedding_service.embed_text(text)
                return ToolResult(
                    success=True,
                    data=embedding,
                    metadata={"dim": len(embedding)}
                )
            elif batch is not None:
                embeddings = self.embedding_service.embed_batch(batch)
                return ToolResult(
                    success=True,
                    data=embeddings,
                    metadata={"count": len(embeddings), "dim": len(embeddings[0]) if embeddings else 0}
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    error="Must provide either 'text' or 'batch'"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
