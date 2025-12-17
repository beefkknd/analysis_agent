"""Agent state definitions using TypedDict.

This module defines the state structure that flows through the LangGraph.
State is modified by nodes and persists across the conversation turn.
"""

from typing import TypedDict, Annotated, Literal, Any
from langgraph.graph import add_messages


class IntentContext(TypedDict, total=False):
    """
    User intent classification results.

    Populated by: classify_intent node
    Used by: routing logic to determine next action

    Fields:
        intent_type: Primary intent classification
            - "new_request": New task, ditch existing TODOs
            - "exact_answer": Direct answer to clarification, rerun same TODO
            - "modification": Answer + new requirements, replan TODOs
            - "continuation": User says "continue", execute next TODO
            - "clarification_response": User responding to agent's question

        confidence: LLM confidence score (0.0-1.0)

        todo_list_valid: Whether current active_todo_list is still valid
            - True: User input is exact answer, continue current plan
            - False: User modified requirements, need to replan

        entities: Extracted entity mentions from user input
            Example: {"vessel": ["MSC ANNA"], "port": ["SHANGHAI"]}

        aggregation_keywords: Time/aggregation indicators
            Example: ["latest", "last week", "average"]

        time_range: Parsed time range if present
            Example: {"start": "2024-01-01", "end": "2024-01-07", "type": "relative"}

        requires_clarification: What needs clarification before proceeding
            Example: ["entity:vessel:Anna", "field:arrival_date"]

        rewritten_question: Clean rewrite after intent reiteration (if needed)
            Example: "Show all shipments to Port of Miami in the last 7 days"
    """
    intent_type: Literal["new_request", "exact_answer", "modification", "continuation", "clarification_response"]
    confidence: float
    todo_list_valid: bool  # NEW: Is current TODO list still valid?

    # Entity extraction
    entities: dict[str, list[str]]
    aggregation_keywords: list[str]
    time_range: dict[str, Any] | None

    # Clarification needs
    requires_clarification: list[str]
    rewritten_question: str | None


class TodoListContext(TypedDict, total=False):
    """
    Active TODO list for current request.

    Populated by: plan_todos node
    Updated by: execute_next_todo node (marks complete, moves pointer)
    Invalidated by: classify_intent node (if user modifies request)

    Fields:
        tasks: Dictionary of all tasks in this plan
            Key: string task identifier (e.g., "resolve_entities", "build_query")
            Value: Task definition with tool, params, status

        current_task_key: Pointer to currently executing task

        total_tasks: Total number of tasks in plan

        completed_tasks: List of completed task keys

        created_at_turn_id: Which turn created this TODO list

        query_strategy: Overall execution strategy
            - "elasticsearch": ES-only query
            - "graphql": GraphQL-only query
            - "hybrid": Combine both sources

    Example:
        {
            "tasks": {
                "resolve_entities": {
                    "tool": "entity_resolution",
                    "params": {"entities": {"vessel": ["Anna"]}},
                    "status": "completed",
                    "result": {...}
                },
                "map_fields": {
                    "tool": "field_mapping",
                    "params": {"fields": ["vessel_name", "arrival_date"]},
                    "status": "in_progress",
                    "result": None
                },
                "build_query": {
                    "tool": "es_query_builder",
                    "params": {...},
                    "status": "pending",
                    "result": None
                }
            },
            "current_task_key": "map_fields",
            "total_tasks": 3,
            "completed_tasks": ["resolve_entities"],
            "query_strategy": "elasticsearch"
        }
    """
    tasks: dict[str, dict[str, Any]]  # {task_key: {tool, params, status, result}}
    current_task_key: str | None  # Pointer to current task
    total_tasks: int
    completed_tasks: list[str]
    created_at_turn_id: int
    query_strategy: Literal["elasticsearch", "graphql", "hybrid"]


class ResolutionContext(TypedDict, total=False):
    """
    Entity resolution state.

    Populated by: entity_resolution tool (via execute_next_todo)
    Used by: Subsequent tools that need resolved entity IDs/names

    Fields:
        unresolved_entities: Original user mentions not yet resolved
            Example: {"vessel": ["Anna", "Maria"]}

        resolved_entities: Successfully resolved entities with IDs
            Example: {"vessel": [{"name": "MSC ANNA", "id": "IMO9876543", "confidence": 0.95}]}

        ambiguous_entities: Multiple matches found, needs clarification
            Example: {"port": [
                {"name": "Port of Miami", "id": "USMIAMI1"},
                {"name": "Miami Container Terminal", "id": "USMIAMI2"}
            ]}

        field_mappings: Database field mappings for each entity type
            Example: {
                "vessel": {
                    "source": "elasticsearch",
                    "field": "vessel_name",
                    "candidates": ["vessel.name", "vessel_name", "vesselName"]
                }
            }

        resolution_metadata: Additional context from resolution process
            Example: {"source": "vector_db", "search_method": "semantic"}
    """
    unresolved_entities: dict[str, list[str]]
    resolved_entities: dict[str, list[dict]]
    ambiguous_entities: dict[str, list[dict]]
    field_mappings: dict[str, dict]
    resolution_metadata: dict[str, Any]


class QueryContext(TypedDict, total=False):
    """
    Query construction and validation state.

    Populated by: query_builder tools (via execute_next_todo)
    Used by: query executor tools

    Fields:
        query_mode: Whether creating new or editing existing

        query_type: Which query engine to use

        es_query: Full Elasticsearch query DSL
            Example: {"query": {"bool": {"must": [...]}}, "size": 1000}

        graphql_query: GraphQL query string with variables
            Example: {
                "query": "query GetShipments($vessel: String) { ... }",
                "variables": {"vessel": "MSC ANNA"}
            }

        previous_query: Previous query for edit operations

        query_plan: Execution strategy
            Example: {
                "strategy": "direct",
                "estimated_records": 150,
                "data_sources": ["elasticsearch"]
            }

        validation_errors: Any validation issues found
            Example: ["Missing required field: port_id", "Invalid date format"]

        needs_approval: Whether user approval required (YOLO mode check)

        user_approved: User's approval decision (None if not asked yet)
    """
    query_mode: Literal["create_new", "edit_existing"]
    query_type: Literal["elasticsearch", "graphql", "hybrid"]
    es_query: dict | None
    graphql_query: dict | None  # {query: str, variables: dict}
    previous_query: dict | None
    query_plan: dict
    validation_errors: list[str]
    needs_approval: bool
    user_approved: bool | None


class ExecutionContext(TypedDict, total=False):
    """
    Query execution results and metadata.

    Populated by: executor tools (via execute_next_todo)
    Used by: response formatting, memory persistence

    Fields:
        raw_results: Raw query results from data source
            Example: {"hits": {"total": 42, "hits": [...]}}

        record_count: Number of records returned

        execution_time_ms: Query execution time

        data_sources_used: Which sources were queried
            Example: ["elasticsearch", "graphql"]

        query_metadata: Structured metadata for future analysis
            This is what gets saved to memory for "analyze X" follow-ups
            Example: {
                "query_type": "elasticsearch",
                "query_structure": {
                    "filters": ["vessel:MSC ANNA", "port:SHANGHAI"],
                    "time_range": "last_7_days",
                    "fields": ["vessel_name", "arrival_date", "status"]
                },
                "result_summary": "42 shipments to Shanghai in last 7 days",
                "how_to_retrieve": {
                    "index": "shipments",
                    "query": {...}  # Full query for re-execution
                }
            }
    """
    raw_results: dict
    record_count: int
    execution_time_ms: float
    data_sources_used: list[str]
    query_metadata: dict  # For analysis forwarding


class BIAgentState(TypedDict, total=False):
    """
    Root agent state - represents state within a single conversation turn.

    This flows through all nodes in the graph and is checkpointed after each turn.

    State Lifecycle:
        1. Initialized at start of turn with user_input, turn_id
        2. classify_intent populates intent context, checks TODO list validity
        3. If needed, plan_todos creates new active_todo_list
        4. execute_next_todo executes tasks, updates contexts, moves pointer
        5. Final response formatted, state saved to memory

    Fields:
        messages: LangGraph message history (for this turn only)
            Annotated with add_messages for automatic message accumulation

        current_turn_id: Sequential turn counter across conversation

        user_input: Raw user input for this turn

        intent: Intent classification results (see IntentContext)

        active_todo_list: Current task plan (see TodoListContext)
            - Created by plan_todos
            - Updated by execute_next_todo
            - Invalidated by classify_intent if user modifies request

        resolution: Entity resolution results (see ResolutionContext)

        query: Query construction state (see QueryContext)

        execution: Query execution results (see ExecutionContext)

        memory: Reference to ShortTermMemory (injected at runtime, not serialized)

        current_phase: Which node we're currently in
            Values: "classify_intent", "reiterate_intention", "plan_todos",
                   "execute_next_todo", "format_response", "clarification"

        iteration_count: Safety counter to prevent infinite loops

        error: Any error that occurred during turn

        agent_response: Final response to return to user

    Implementation Notes:
        - Use total=False to allow incremental state building
        - Nested contexts (intent, resolution, etc.) are populated by specific nodes
        - active_todo_list is the key to cyclic flow - checked at start of every turn
    """

    # LangGraph message history (for this turn)
    messages: Annotated[list, add_messages]

    # Current turn metadata
    current_turn_id: int
    user_input: str

    # Phase-specific contexts (populated as turn progresses)
    intent: IntentContext
    active_todo_list: TodoListContext  # NEW: Active TODO list for current request
    resolution: ResolutionContext
    query: QueryContext
    execution: ExecutionContext

    # Memory reference (injected at runtime, not serialized)
    memory: Any  # ShortTermMemory - avoid circular import

    # Workflow control
    current_phase: Literal[
        "classify_intent",
        "reiterate_intention",
        "plan_todos",
        "execute_next_todo",
        "format_response",
        "clarification"
    ]
    iteration_count: int
    error: str | None

    # Output
    agent_response: str | None
