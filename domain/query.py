"""Query domain objects.

Represents queries across different data sources (Elasticsearch, GraphQL).
"""

from pydantic import BaseModel, Field
from typing import Any, Literal


class QueryPlan(BaseModel):
    """
    Query execution strategy.

    Determined by plan_todos node when creating TODO list.

    Fields:
        strategy: Execution approach
            - "direct": Single data source query
            - "parallel": Multiple sources queried concurrently
            - "sequential": Multiple sources queried in order

        estimated_records: Expected result count (rough estimate)
            Example: 150
            Used for: pagination decisions, timeout settings

        data_sources: Which sources will be queried
            Example: ["elasticsearch"], ["graphql"], or ["elasticsearch", "graphql"]

        timeout_ms: Query timeout in milliseconds
            Example: 30000 (30 seconds)

        pagination: Pagination settings
            Example: {"page_size": 1000, "max_pages": 10}

    Example:
        QueryPlan(
            strategy="direct",
            estimated_records=150,
            data_sources=["elasticsearch"],
            timeout_ms=30000,
            pagination={"page_size": 1000}
        )

    Implementation Notes:
        - Created by plan_todos based on intent classification
        - Used by query executor to configure execution
        - Affects TODO breakdown (parallel sources = separate TODOs)
    """
    strategy: Literal["direct", "parallel", "sequential"]
    estimated_records: int = 0
    data_sources: list[str] = Field(default_factory=list)
    timeout_ms: int = 30000
    pagination: dict[str, Any] = Field(default_factory=dict)

    def needs_parallel_execution(self) -> bool:
        """Check if parallel execution required."""
        return self.strategy == "parallel" and len(self.data_sources) > 1

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()


class ElasticsearchQuery(BaseModel):
    """
    Elasticsearch query wrapper.

    Built by es_query_builder tool, executed by es_executor tool.

    Fields:
        query: Full Elasticsearch query DSL
            Example: {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"vessel_name": "MSC ANNA"}},
                            {"range": {"arrival_date": {"gte": "2024-01-01"}}}
                        ]
                    }
                },
                "size": 1000,
                "sort": [{"arrival_date": "desc"}]
            }

        index: Target Elasticsearch index
            Example: "shipments", "vessels", "ports"

        size: Maximum results to return
            Example: 1000

        timeout_ms: Query timeout in milliseconds
            Example: 30000 (30 seconds)

        search_type: Elasticsearch search type
            Example: "query_then_fetch", "dfs_query_then_fetch"

        metadata: Additional context
            Example: {
                "query_summary": "Search shipments by vessel and port",
                "filters_applied": ["vessel:MSC ANNA", "port:SHANGHAI"],
                "time_range": "last_7_days"
            }

    Example:
        ElasticsearchQuery(
            query={"query": {"bool": {"must": [...]}}},
            index="shipments",
            size=1000,
            timeout_ms=30000,
            metadata={"query_summary": "Search shipments by vessel"}
        )

    Implementation Notes:
        - Built by es_query_builder tool with LLM assistance
        - Validated before execution
        - Metadata saved to query_metadata for future analysis
    """
    query: dict[str, Any]
    index: str
    size: int = 1000
    timeout_ms: int = 30000
    search_type: str = "query_then_fetch"
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    def get_filter_summary(self) -> list[str]:
        """
        Extract human-readable filter summary.

        Returns:
            List of applied filters
            Example: ["vessel:MSC ANNA", "port:SHANGHAI", "date:last_7_days"]

        Implementation Notes:
            - Parse query DSL to extract filters
            - Used for query_metadata summary
            - Helps with "analyze X" follow-up requests
        """
        # TODO: Parse query["query"]["bool"]["must"] to extract filters
        # Return list of "field:value" strings
        raise NotImplementedError("Parse ES query filters")


class GraphQLQuery(BaseModel):
    """
    GraphQL query wrapper.

    Built by graphql_query_builder tool, executed by graphql_executor tool.

    Fields:
        query: GraphQL query string
            Example: '''
                query GetShipments($vessel: String, $port: String) {
                    shipments(vessel: $vessel, port: $port) {
                        id
                        vessel_name
                        arrival_date
                        status
                    }
                }
            '''

        variables: Query variables
            Example: {"vessel": "MSC ANNA", "port": "SHANGHAI"}

        operation_name: Optional operation name
            Example: "GetShipments"
            Used when query contains multiple operations

        timeout_ms: Query timeout in milliseconds
            Example: 30000

        metadata: Additional context
            Example: {
                "query_summary": "Fetch shipments with vessel and port filters",
                "fields_requested": ["vessel_name", "arrival_date", "status"],
                "filters_applied": ["vessel:MSC ANNA"]
            }

    Example:
        GraphQLQuery(
            query="query GetShipments($vessel: String) { ... }",
            variables={"vessel": "MSC ANNA"},
            operation_name="GetShipments",
            metadata={"query_summary": "Fetch shipments by vessel"}
        )

    Implementation Notes:
        - Built by graphql_query_builder tool with LLM assistance
        - Variables used for parameterization
        - Metadata saved for future analysis
    """
    query: str
    variables: dict[str, Any] = Field(default_factory=dict)
    operation_name: str | None = None
    timeout_ms: int = 30000
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    def get_filter_summary(self) -> list[str]:
        """
        Extract human-readable filter summary from variables.

        Returns:
            List of applied filters
            Example: ["vessel:MSC ANNA", "port:SHANGHAI"]

        Implementation Notes:
            - Parse variables dict to extract filters
            - Used for query_metadata summary
        """
        filters = []
        for key, value in self.variables.items():
            if value is not None:
                filters.append(f"{key}:{value}")
        return filters


class QueryResult(BaseModel):
    """
    Unified query result across data sources.

    Returned by executor tools (es_executor, graphql_executor).

    Fields:
        success: Whether query succeeded
            True if results returned, False if error

        data: Raw query results
            Example (ES): {"hits": {"total": 42, "hits": [...]}}
            Example (GraphQL): {"data": {"shipments": [...]}}

        record_count: Number of records returned
            Example: 42

        execution_time_ms: Query execution time
            Example: 235.5

        data_source: Which source was queried
            Example: "elasticsearch", "graphql"

        error: Error message if failed
            Example: "Timeout after 30000ms"

        metadata: Additional context
            Example: {
                "index": "shipments",
                "query_summary": "Search shipments by vessel",
                "cached": False
            }

    Example:
        QueryResult(
            success=True,
            data={"hits": {"total": 42, "hits": [...]}},
            record_count=42,
            execution_time_ms=235.5,
            data_source="elasticsearch",
            metadata={"index": "shipments"}
        )

    Implementation Notes:
        - Unified interface across ES and GraphQL
        - Used by execute_next_todo to populate ExecutionContext
        - Converted to user-friendly format by response formatter
    """
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    record_count: int = 0
    execution_time_ms: float = 0.0
    data_source: Literal["elasticsearch", "graphql"] = "elasticsearch"
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def has_results(self) -> bool:
        """Check if query returned any results."""
        return self.success and self.record_count > 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()


class QueryMetadata(BaseModel):
    """
    Structured metadata for query results.

    This is what gets saved to ConversationTurn.query_metadata
    for future "analyze X" requests.

    Fields:
        query_type: Which data source was used
            Example: "elasticsearch", "graphql", "hybrid"

        query_structure: Structured breakdown of query
            Example: {
                "filters": ["vessel:MSC ANNA", "port:SHANGHAI"],
                "time_range": "last_7_days",
                "fields": ["vessel_name", "arrival_date", "status"],
                "aggregations": []
            }

        result_summary: Human-readable summary
            Example: "Found 42 shipments to Shanghai in last 7 days"

        how_to_retrieve: Full query for re-execution
            Example (ES): {
                "index": "shipments",
                "query": {"query": {"bool": {...}}},
                "size": 1000
            }
            Example (GraphQL): {
                "query": "query GetShipments { ... }",
                "variables": {"vessel": "MSC ANNA"}
            }

        record_count: Number of results
            Example: 42

        data_source: Which source was queried
            Example: "elasticsearch"

    Example:
        QueryMetadata(
            query_type="elasticsearch",
            query_structure={
                "filters": ["vessel:MSC ANNA"],
                "time_range": "last_7_days",
                "fields": ["vessel_name", "arrival_date"]
            },
            result_summary="Found 42 shipments",
            how_to_retrieve={"index": "shipments", "query": {...}},
            record_count=42,
            data_source="elasticsearch"
        )

    Implementation Notes:
        - Created by execute_next_todo after successful query
        - Saved to ConversationTurn.query_metadata
        - Used by future "analyze X" requests to re-fetch data
        - Must be complete enough to reconstruct query
    """
    query_type: Literal["elasticsearch", "graphql", "hybrid"]
    query_structure: dict[str, Any] = Field(default_factory=dict)
    result_summary: str
    how_to_retrieve: dict[str, Any] = Field(default_factory=dict)
    record_count: int = 0
    data_source: str = "elasticsearch"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    def can_be_analyzed(self) -> bool:
        """
        Check if this query result can be analyzed.

        Returns:
            True if has data and structure for analysis

        Implementation Notes:
            - Need record_count > 0
            - Need how_to_retrieve populated
            - Used to determine if "analyze X" is possible
        """
        return (
            self.record_count > 0
            and len(self.how_to_retrieve) > 0
            and len(self.query_structure) > 0
        )
