"""Field mapping tool - maps business entities to database schema fields."""

from tools.base import BaseTool, ToolResult
from services.vectordb_service import VectorDBService


class FieldMappingTool(BaseTool):
    """
    Maps resolved business entities to database schema fields (ES/GraphQL).

    Uses vector search to find matching field names from schema embeddings.
    Returns top 3 candidates for LLM to decide which field is best fit.

    Example:
        Input: entity_name="MSC ANNA", entity_type="vessel", source="elasticsearch"
        Output: [
            {"field": "vessel_name", "description": "Full vessel name", "type": "string"},
            {"field": "vessel_imo", "description": "IMO number", "type": "string"},
            {"field": "vessel_id", "description": "Internal ID", "type": "integer"}
        ]
    """

    def __init__(self, vectordb_service: VectorDBService):
        self.vectordb_service = vectordb_service

    @property
    def name(self) -> str:
        return "field_mapping"

    @property
    def description(self) -> str:
        return "Map business entity to database schema field names (ES/GraphQL)"

    def input_schema(self) -> dict:
        """MCP-compatible input schema."""
        return {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "The resolved entity name (e.g., 'MSC ANNA')"
                },
                "entity_type": {
                    "type": "string",
                    "description": "The entity type (e.g., 'vessel', 'port', 'shipper')"
                },
                "source": {
                    "type": "string",
                    "enum": ["elasticsearch", "graphql", "any"],
                    "description": "Target data source for field mapping"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of field candidates to return (default 3)",
                    "default": 3
                }
            },
            "required": ["entity_name", "entity_type", "source"]
        }

    def execute(
        self,
        entity_name: str,
        entity_type: str,
        source: str = "any",
        top_k: int = 3
    ) -> ToolResult:
        """
        Execute field mapping via vector search.

        Query pattern: "{entity_type} field for {source}"
        Filter: {"entity_type": entity_type, "source": source}
        """
        try:
            # Build query text
            query_text = f"{entity_type} field for {source}"

            # Build filter
            filter_dict = {"entity_type": entity_type}
            if source != "any":
                filter_dict["source"] = source

            # Query vector DB for field mappings
            # Collection name: "schema_field_mappings"
            results = self.vectordb_service.query(
                query_text=query_text,
                collection="schema_field_mappings",
                filter_dict=filter_dict,
                limit=top_k
            )

            # Format results
            candidates = []
            for result in results:
                metadata = result.get("metadata", {})
                candidates.append({
                    "field": metadata.get("field_name", "unknown"),
                    "source": metadata.get("source", "unknown"),
                    "description": metadata.get("description", ""),
                    "field_type": metadata.get("field_type", "string"),
                    "example_values": metadata.get("example_values", []),
                    "similarity_score": 1.0 - result.get("distance", 0.0)  # Convert distance to similarity
                })

            return ToolResult(
                success=True,
                data={
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "source": source,
                    "candidates": candidates,
                    "count": len(candidates)
                },
                metadata={
                    "query_text": query_text,
                    "filter": filter_dict
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Field mapping failed: {str(e)}"
            )
