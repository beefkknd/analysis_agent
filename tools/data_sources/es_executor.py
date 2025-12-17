"""Elasticsearch query execution tool."""

from tools.base import BaseTool, ToolResult
from elasticsearch import Elasticsearch
from config.settings import Settings


class ESExecutorTool(BaseTool):
    """
    Stateless Elasticsearch query executor.

    Input: ES query dict + execution config
    Output: Results dict + metadata
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = Elasticsearch([settings.es_url])

    @property
    def name(self) -> str:
        return "es_executor"

    @property
    def description(self) -> str:
        return "Execute Elasticsearch query and return results"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "object",
                    "description": "Elasticsearch query DSL"
                },
                "index": {
                    "type": "string",
                    "description": "Index name"
                },
                "size": {
                    "type": "integer",
                    "default": 1000,
                    "description": "Max results to return"
                },
                "timeout_ms": {
                    "type": "integer",
                    "default": 30000,
                    "description": "Query timeout in milliseconds"
                },
            },
            "required": ["query", "index"]
        }

    def execute(
        self,
        query: dict,
        index: str,
        size: int = 1000,
        timeout_ms: int = 30000,
    ) -> ToolResult:
        """
        Execute Elasticsearch query.

        Args:
            query: ES query DSL dict
            index: Index name
            size: Max results
            timeout_ms: Timeout in milliseconds
        """
        try:
            response = self.client.search(
                index=index,
                body=query,
                size=size,
                request_timeout=timeout_ms / 1000,  # Convert to seconds
            )

            return ToolResult(
                success=True,
                data={
                    "hits": [hit["_source"] for hit in response["hits"]["hits"]],
                    "total": response["hits"]["total"]["value"],
                    "took_ms": response["took"],
                    "timed_out": response["timed_out"],
                },
                metadata={
                    "index": index,
                    "query": query,
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
