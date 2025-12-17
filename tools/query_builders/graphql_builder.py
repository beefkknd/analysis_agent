"""GraphQL query builder tool."""

from tools.base import BaseTool, ToolResult


class GraphQLQueryBuilderTool(BaseTool):
    """
    Stateless GraphQL query builder.

    Input: Intent structure (entities, fields to fetch)
    Output: GraphQL query string
    """

    @property
    def name(self) -> str:
        return "graphql_query_builder"

    @property
    def description(self) -> str:
        return "Build GraphQL query from intent and entities"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "description": "GraphQL operation type"
                },
                "entities": {
                    "type": "object",
                    "description": "Entity filters"
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to return"
                },
            },
            "required": ["query_type", "entities", "fields"]
        }

    def execute(
        self,
        query_type: str,
        entities: dict,
        fields: list[str],
    ) -> ToolResult:
        """
        Build GraphQL query.

        Args:
            query_type: Type of query
            entities: Entity filters
            fields: Fields to fetch
        """
        try:
            # TODO: Implement GraphQL query building logic
            # This is a placeholder implementation

            variables_def = []
            filters = []

            for entity_type, values in entities.items():
                var_name = f"{entity_type}Filter"
                variables_def.append(f"${var_name}: [String!]")
                filters.append(f"{entity_type}: ${var_name}")

            vars_str = ", ".join(variables_def) if variables_def else ""
            filters_str = ", ".join(filters) if filters else ""
            fields_str = "\n    ".join(fields)

            query = f"""
query GetData({vars_str}) {{
  data({filters_str}) {{
    {fields_str}
  }}
}}
"""

            return ToolResult(
                success=True,
                data=query.strip(),
                metadata={
                    "query_type": query_type,
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
