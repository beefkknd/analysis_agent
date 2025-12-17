"""Plan TODO list for request execution.

Breaks complex request into sequential tasks.
Uses LLM to generate task list with tool assignments.
"""

from domain.state import BIAgentState, TodoListContext
from tools.registry import ToolRegistry
from typing import Literal


def plan_todos(state: BIAgentState, registry: ToolRegistry) -> dict:
    """
    Break request into TODO list with tool assignments.

    Uses LLM for strategic + tactical planning combined:
    - Strategic: What needs to be done (resolve entities, build query, execute)
    - Tactical: Which tools to use, in what order, with what params

    Purpose:
        - Create executable task list
        - Assign tools to tasks
        - Determine execution strategy (ES vs GraphQL vs hybrid)
        - Show plan to user ("Starting task 1 of 5...")

    Args:
        state: Current agent state with:
            - user_input: User message
            - intent: IntentContext with entities, rewritten_question
            - memory: ShortTermMemory
        registry: Tool registry for introspection and execution

    Returns:
        State updates:
            {
                "active_todo_list": TodoListContext {
                    "tasks": {
                        "resolve_entities": {
                            "tool": "entity_resolution",
                            "params": {"entities": {...}, "context": "..."},
                            "status": "pending",
                            "result": None
                        },
                        "map_fields": {...},
                        "build_query": {...},
                        "execute_query": {...},
                        "format_results": {...}
                    },
                    "current_task_key": "resolve_entities",
                    "total_tasks": 5,
                    "completed_tasks": [],
                    "created_at_turn_id": 1,
                    "query_strategy": "elasticsearch"
                },
                "current_phase": "plan_todos"
            }

    State Updates:
        - active_todo_list: TodoListContext with task breakdown
        - current_phase: "plan_todos"

    Implementation Flow:
        1. Extract intent and rewritten question
        2. Determine query strategy (ES vs GraphQL vs hybrid)
           Based on: entities, data freshness needs, aggregation complexity
        3. Introspect available tools from registry
        4. Build planning prompt with:
           - rewritten_question
           - extracted entities
           - available tools (names + descriptions)
           - query strategy decision
        5. Call LLM to generate TODO list
        6. Parse LLM response into TodoListContext
        7. Set current_task_key to first task
        8. Return state updates

    Typical TODO Sequences:

    Example 1: Simple Entity Query (ES)
        User: "Show shipments to Port of Miami last week"
        Strategy: elasticsearch
        TODOs:
            1. resolve_entities: Resolve "Port of Miami"
            2. map_fields: Map "shipments", "arrival_date" to ES fields
            3. build_query: Construct ES query with filters
            4. execute_query: Run ES query
            5. format_results: Format for user

    Example 2: Complex Query with Clarification (ES)
        User: "Show shipments from Anna to Miami"
        Strategy: elasticsearch
        TODOs:
            1. resolve_entities: Resolve "Anna" (vessel) and "Miami" (port)
               - May trigger clarification if ambiguous
            2. map_fields: Map fields
            3. build_query: ES query
            4. execute_query: Execute
            5. format_results: Format

    Example 3: GraphQL Query
        User: "Show vessel schedule for MSC ANNA"
        Strategy: graphql (real-time schedule data)
        TODOs:
            1. resolve_entities: Resolve vessel
            2. map_fields: Map to GraphQL schema
            3. build_query: Construct GraphQL query
            4. execute_query: Run GraphQL
            5. format_results: Format

    Example 4: Hybrid Query
        User: "Compare historical shipments vs current schedule"
        Strategy: hybrid (ES for history, GraphQL for schedule)
        TODOs:
            1. resolve_entities: Resolve entities
            2. map_fields_es: Map to ES schema
            3. build_query_es: ES query
            4. execute_query_es: Run ES
            5. map_fields_graphql: Map to GraphQL schema
            6. build_query_graphql: GraphQL query
            7. execute_query_graphql: Run GraphQL
            8. merge_results: Combine results
            9. format_results: Format

    Example 5: Data Analysis (After Query)
        User: "Analyze delay patterns" (after previous shipment query)
        Strategy: analysis (retrieve from query_metadata)
        TODOs:
            1. retrieve_data: Re-fetch from query_metadata
            2. analyze_patterns: Run pattern analysis
            3. format_results: Format findings

    Task Structure:
        Each task has:
            - tool: Tool name to execute (from registry)
            - params: Tool-specific parameters
            - status: "pending" | "in_progress" | "completed"
            - result: ToolResult after execution (None initially)

    Query Strategy Selection:
        Elasticsearch:
            - Historical data queries
            - Aggregations (count, average, sum)
            - Full-text search
            - Complex filters

        GraphQL:
            - Real-time data (current status, schedules)
            - Relationship queries (nested data)
            - Strongly typed fields

        Hybrid:
            - Comparison queries (historical vs current)
            - Join-like operations across sources

    Tool Selection:
        LLM-enabled (can clarify):
            - entity_resolution: Resolve entity mentions
            - field_mapping: Map business terms to schema
            - query_builder: Construct queries (es_query_builder, graphql_query_builder)

        Traditional (direct execution):
            - es_executor: Run ES query
            - graphql_executor: Run GraphQL query

        Analysis (future):
            - stats_analysis: Statistical analysis
            - pattern_recognition: Pattern detection

    Implementation Notes:
        - Use llm_tool with structured output (TodoListContext schema)
        - LLM should see all available tools via registry.list_tools()
        - Task keys should be descriptive strings (not indices)
        - First task should be set as current_task_key
        - all tasks start with status="pending"
        - Include turn_id in TodoListContext for tracking

    Prompt Template (Pseudocode):
        ```
        You are a planning agent for business intelligence queries.

        User request: "{rewritten_question}"

        Extracted entities: {entities}
        Time range: {time_range}
        Query strategy: {query_strategy} (elasticsearch/graphql/hybrid)

        Available tools:
        {tool_list_with_descriptions}

        Break this request into a TODO list. Each task should:
        1. Have a descriptive key (snake_case)
        2. Specify which tool to use
        3. Include tool parameters
        4. Be executable independently

        Typical flow:
        1. resolve_entities: Clarify entity mentions
        2. map_fields: Map to database schema
        3. build_query: Construct query
        4. execute_query: Run query
        5. format_results: Format output

        Return JSON matching TodoListContext schema.
        Include tasks dict, total_tasks, query_strategy.
        ```

    Error Handling:
        - If LLM fails, use default TODO list based on intent type
        - If no tasks generated, create minimal list (execute → format)
        - Validate task keys are unique

    Validation:
        - Check tasks not empty
        - Check all tools referenced exist in registry
        - Check task_keys are unique
        - Check first task makes sense (usually resolve_entities or map_fields)

    User Communication:
        - After planning, show user: "I'll execute 5 tasks: resolve entities, map fields, ..."
        - Build this message in format_results or separate communication node

    Raises:
        Should NOT raise - return error in state instead
    """
    # TODO: Extract intent and question
    # intent = state.get("intent", {})
    # rewritten_question = intent.get("rewritten_question") or state["user_input"]
    # entities = intent.get("entities", {})
    # time_range = intent.get("time_range")

    # TODO: Determine query strategy
    # query_strategy = determine_query_strategy(
    #     intent=intent,
    #     entities=entities,
    #     time_range=time_range
    # )

    # TODO: Get available tools
    # available_tools = registry.list_tools()
    # tool_descriptions = {
    #     name: registry.get_tool_info(name)["description"]
    #     for name in available_tools
    # }

    # TODO: Build planning prompt
    # prompt = build_planning_prompt(
    #     rewritten_question=rewritten_question,
    #     entities=entities,
    #     time_range=time_range,
    #     query_strategy=query_strategy,
    #     available_tools=tool_descriptions
    # )

    # TODO: Call LLM to generate TODO list
    # result = registry.execute(
    #     "llm_tool",
    #     prompt=prompt,
    #     output_schema=TodoListContext.__annotations__,
    #     temperature=0.2  # Moderate temp for creative but consistent planning
    # )

    # TODO: Parse and validate TODO list
    # if result.success:
    #     todo_data = result.data
    #     todo_list = validate_and_build_todo_list(
    #         todo_data=todo_data,
    #         registry=registry,
    #         turn_id=state["current_turn_id"],
    #         query_strategy=query_strategy
    #     )
    # else:
    #     # Fallback to default TODO list
    #     todo_list = create_default_todo_list(
    #         intent=intent,
    #         query_strategy=query_strategy,
    #         turn_id=state["current_turn_id"]
    #     )

    # TODO: Return state updates
    # return {
    #     "active_todo_list": todo_list,
    #     "current_phase": "plan_todos"
    # }

    raise NotImplementedError("Implement TODO planning logic")


def determine_query_strategy(
    intent: dict,
    entities: dict,
    time_range: dict | None
) -> Literal["elasticsearch", "graphql", "hybrid"]:
    """
    Determine which data source(s) to query.

    Args:
        intent: IntentContext dict
        entities: Extracted entities
        time_range: Time range (if present)

    Returns:
        Query strategy: "elasticsearch", "graphql", or "hybrid"

    Decision Logic:
        Elasticsearch:
            - Historical data (has time_range in past)
            - Aggregations (count, average, keywords present)
            - Full-text search

        GraphQL:
            - Real-time data (current status, live schedule)
            - No time range or time_range is "now"
            - Relationship queries

        Hybrid:
            - Explicit comparison ("historical vs current")
            - Multiple data needs

    Implementation Notes:
        - Can use LLM for decision if complex
        - Use heuristics for simple cases
        - Default to elasticsearch for ambiguous cases
    """
    # TODO: Implement strategy selection logic
    # Check for aggregation keywords → elasticsearch
    # Check for real-time keywords ("current", "now") → graphql
    # Check for comparison keywords → hybrid
    # Default → elasticsearch
    raise NotImplementedError("Determine query strategy")


def build_planning_prompt(
    rewritten_question: str,
    entities: dict,
    time_range: dict | None,
    query_strategy: str,
    available_tools: dict
) -> str:
    """
    Build planning prompt for LLM.

    Args:
        rewritten_question: Clean user question
        entities: Extracted entities
        time_range: Time range
        query_strategy: Query strategy decision
        available_tools: Dict of tool_name → description

    Returns:
        Formatted prompt for LLM

    Implementation Notes:
        - Include tool catalog with descriptions
        - Show typical TODO sequences as examples
        - Emphasize task independence
    """
    # TODO: Build prompt with examples
    raise NotImplementedError("Build planning prompt")


def validate_and_build_todo_list(
    todo_data: dict,
    registry: ToolRegistry,
    turn_id: int,
    query_strategy: str
) -> dict:
    """
    Validate and construct TodoListContext.

    Args:
        todo_data: LLM output
        registry: Tool registry for validation
        turn_id: Current turn ID
        query_strategy: Query strategy

    Returns:
        Valid TodoListContext dict

    Validation:
        - All tools exist in registry
        - Task keys are unique
        - At least one task present
        - First task is reasonable

    Implementation Notes:
        - Add missing fields (status="pending", result=None)
        - Set current_task_key to first task
        - Add turn_id and query_strategy
    """
    # TODO: Validate and construct
    raise NotImplementedError("Validate TODO list")


def create_default_todo_list(
    intent: dict,
    query_strategy: str,
    turn_id: int
) -> dict:
    """
    Create fallback TODO list if LLM planning fails.

    Args:
        intent: IntentContext dict
        query_strategy: Query strategy
        turn_id: Current turn ID

    Returns:
        Minimal TodoListContext dict

    Implementation Notes:
        - Basic sequence: resolve → map → build → execute → format
        - Use intent entities for parameters
        - Should always work as fallback
    """
    # TODO: Create minimal TODO list
    raise NotImplementedError("Create default TODO list")
