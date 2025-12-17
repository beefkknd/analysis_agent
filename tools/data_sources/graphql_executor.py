"""GraphQL query execution tool."""

from tools.base import BaseTool, ToolResult
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from config.settings import Settings


class GraphQLExecutorTool(BaseTool):
    """
    Stateless GraphQL query executor.

    Input: GraphQL query string + variables
    Output: Query results
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        transport = RequestsHTTPTransport(url=settings.graphql_endpoint)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    @property
    def name(self) -> str:
        return "graphql_executor"

    @property
    def description(self) -> str:
        return "Execute GraphQL query and return results"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "GraphQL query string"
                },
                "variables": {
                    "type": "object",
                    "description": "Query variables",
                    "default": {}
                },
                "operation_name": {
                    "type": "string",
                    "description": "Operation name (optional)"
                },
            },
            "required": ["query"]
        }

    def execute(
        self,
        query: str,
        variables: dict | None = None,
        operation_name: str | None = None,
    ) -> ToolResult:
        """
        Execute GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables
            operation_name: Operation name
        """
        try:
            gql_query = gql(query)
            result = self.client.execute(
                gql_query,
                variable_values=variables or {},
                operation_name=operation_name,
            )

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "operation_name": operation_name,
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
