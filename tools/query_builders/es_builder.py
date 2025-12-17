"""Elasticsearch query builder tool."""

from tools.base import BaseTool, ToolResult


class ESQueryBuilderTool(BaseTool):
    """
    Stateless ES query builder.

    Input: Intent structure (entities, time range, filters)
    Output: ES query dict
    """

    @property
    def name(self) -> str:
        return "es_query_builder"

    @property
    def description(self) -> str:
        return "Build Elasticsearch query from intent and entities"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "intent_type": {
                    "type": "string",
                    "enum": ["lookup", "aggregation", "comparison", "trend"]
                },
                "entities": {
                    "type": "object",
                    "description": "Entity dict: entity_type -> list of values"
                },
                "time_range": {
                    "type": "object",
                    "description": "Time range filter"
                },
                "filters": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Additional filters"
                },
                "aggregations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Aggregation field names"
                },
            },
            "required": ["intent_type", "entities"]
        }

    def execute(
        self,
        intent_type: str,
        entities: dict,
        time_range: dict | None = None,
        filters: list[dict] | None = None,
        aggregations: list[str] | None = None,
    ) -> ToolResult:
        """
        Build ES query from intent parameters.

        Args:
            intent_type: Type of query (lookup, aggregation, etc.)
            entities: Resolved entities dict
            time_range: Time range filter
            filters: Additional filters
            aggregations: Fields to aggregate
        """
        try:
            # Build must clauses from entities
            must_clauses = []
            for entity_type, values in entities.items():
                if values:
                    must_clauses.append({
                        "terms": {f"{entity_type}_name": values}
                    })

            # Build time filter
            filter_clauses = []
            if time_range:
                filter_clauses.append({
                    "range": {
                        "timestamp": time_range
                    }
                })

            # Add custom filters
            if filters:
                filter_clauses.extend(filters)

            # Build base query
            query = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses,
                    }
                }
            }

            # Add aggregations if needed
            if aggregations and intent_type == "aggregation":
                query["aggs"] = {}
                for field in aggregations:
                    query["aggs"][f"{field}_stats"] = {
                        "stats": {"field": field}
                    }

            return ToolResult(
                success=True,
                data=query,
                metadata={
                    "intent_type": intent_type,
                    "entity_count": len(entities),
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
