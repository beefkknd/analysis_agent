"""Vector database search tool."""

from tools.base import BaseTool, ToolResult
from services.vectordb_service import VectorDBService
from tools.embedding.embedding_tool import EmbeddingTool


class VectorDBTool(BaseTool):
    """
    Stateless vector search tool.
    Can use embedding_tool internally or receive pre-computed embeddings.
    """

    def __init__(
        self,
        vectordb_service: VectorDBService,
        embedding_tool: EmbeddingTool | None = None
    ):
        self.vectordb_service = vectordb_service
        self.embedding_tool = embedding_tool

    @property
    def name(self) -> str:
        return "vector_search"

    @property
    def description(self) -> str:
        return "Search vector database for similar entities"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Collection/index name"
                },
                "query": {
                    "type": "string",
                    "description": "Search query text (will be embedded)"
                },
                "embedding": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Pre-computed query embedding"
                },
                "top_k": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of results to return"
                },
            },
            "required": ["collection"],
            "oneOf": [
                {"required": ["query"]},
                {"required": ["embedding"]}
            ]
        }

    def execute(
        self,
        collection: str,
        query: str | None = None,
        embedding: list[float] | None = None,
        top_k: int = 5,
    ) -> ToolResult:
        """
        Search vector DB.

        Args:
            collection: Collection/index name
            query: Text query (will be embedded if embedding not provided)
            embedding: Pre-computed embedding
            top_k: Number of results
        """
        try:
            # Get embedding if text provided
            if query and not embedding:
                if not self.embedding_tool:
                    return ToolResult(
                        success=False,
                        data=None,
                        error="No embedding_tool available for text query"
                    )

                embed_result = self.embedding_tool.execute(text=query)
                if not embed_result.success:
                    return embed_result
                embedding = embed_result.data

            if not embedding:
                return ToolResult(
                    success=False,
                    data=None,
                    error="Must provide either 'query' or 'embedding'"
                )

            # Search
            results = self.vectordb_service.search(
                collection=collection,
                query_vector=embedding,
                limit=top_k
            )

            return ToolResult(
                success=True,
                data=results,
                metadata={
                    "collection": collection,
                    "results_count": len(results)
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
