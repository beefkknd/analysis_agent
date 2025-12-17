"""Execute next TODO from active list.

Core execution node that runs tasks one at a time.
Handles success, clarification, and error outcomes.
"""

from domain.state import BIAgentState
from domain.conversation import ConversationTurn, Message
from tools.registry import ToolRegistry
from datetime import datetime


def execute_next_todo(state: BIAgentState, registry: ToolRegistry) -> dict:
    """
    Execute the current TODO task.

    This is the workhorse node that actually executes tools and handles results.
    Called repeatedly in loop until all TODOs complete or clarification needed.

    Execution Flow:
        1. Get current task from active_todo_list
        2. Execute tool with parameters
        3. Handle result:
           - Success: Mark complete, move pointer, continue
           - Clarification: Save memory, end turn, ask user
           - Error: Save memory, end turn, report error
        4. Update state based on tool output
        5. Save memory entry for this TODO

    Args:
        state: Current agent state with:
            - active_todo_list: TodoListContext with current_task_key
            - intent, resolution, query, execution contexts
            - memory: ShortTermMemory
        registry: Tool registry for execution

    Returns:
        State updates based on execution outcome:

        Success (no clarification):
            {
                "active_todo_list": {
                    ...updated with task marked complete, pointer moved
                },
                "resolution": {...} | "query": {...} | "execution": {...},
                  # Depending on which tool executed
                "current_phase": "execute_next_todo",
                "iteration_count": state["iteration_count"] + 1
            }

        Clarification needed:
            {
                "active_todo_list": {...}, # Task status updated but not complete
                "agent_response": "Which Miami do you mean: Port of Miami or Miami Container Terminal?",
                "current_phase": "clarification"
            }

        Error:
            {
                "error": "Entity resolution failed: Connection timeout",
                "agent_response": "I encountered an error: ...",
                "current_phase": "error"
            }

        All TODOs complete:
            {
                "active_todo_list": {
                    ...all tasks completed
                },
                "execution": {
                    "query_metadata": {...}  # For future analysis
                },
                "agent_response": "Found 42 shipments...",
                "current_phase": "format_response"
            }

    State Updates:
        - active_todo_list: Task status updated, pointer moved
        - resolution/query/execution: Populated based on tool
        - agent_response: Set if clarification or final response
        - current_phase: Updated based on outcome
        - iteration_count: Incremented

    Implementation Flow:
        1. Get current task
           - active_todo_list["current_task_key"]
           - tasks[current_task_key]

        2. Mark task as in_progress
           - tasks[task_key]["status"] = "in_progress"

        3. Execute tool
           - tool_name = task["tool"]
           - params = task["params"]
           - result = registry.execute(tool_name, **params)

        4. Handle result
           a) Success + No clarification:
              - Store result in task["result"]
              - Mark task status = "completed"
              - Update appropriate context (resolution/query/execution)
              - Move pointer to next task or END
              - Save memory entry
              - Return state updates

           b) Success + Clarification needed:
              - Store partial result
              - Build clarification message
              - Set agent_response
              - Save memory entry with clarification
              - END TURN (return with current_phase="clarification")

           c) Error:
              - Store error
              - Build error message
              - Set agent_response
              - Save memory entry with error
              - END TURN (return with current_phase="error")

        5. Check if more TODOs
           - If current_task_key is None (all done):
               - Build final response
               - Save query_metadata
               - Return with current_phase="format_response"
           - Else:
               - Return with current_phase="execute_next_todo" (loop continues)

    Tool Result Handling by Type:

    1. entity_resolution tool:
       - Success: Update resolution context with resolved entities
       - Clarification: Return ambiguous entities as question
       - Error: Report resolution failure

    2. field_mapping tool:
       - Success: Update resolution context with field mappings
       - Clarification: Ask about ambiguous field names
       - Error: Report mapping failure

    3. query_builder tools (es_query_builder, graphql_query_builder):
       - Success: Update query context with constructed query
       - Clarification: Ask about query parameters (rare)
       - Error: Report query construction failure

    4. executor tools (es_executor, graphql_executor):
       - Success: Update execution context with results
       - Error: Report query execution failure
       - No clarification (traditional tool)

    Memory Saving:

    After each TODO execution, save ConversationTurn:
        ConversationTurn(
            turn_id=state["current_turn_id"],
            user_message=Message(role="user", content=state["user_input"]),
            agent_response=Message(role="assistant", content=response_text),
            intent_detected=state["intent"]["intent_type"],
            rewritten_question=state["intent"].get("rewritten_question"),
            entities_extracted=get_resolved_entities(state),
            queries_executed=get_queries_executed(state),
            query_metadata=build_query_metadata(state),
            tokens_used=calculate_tokens(state)
        )

    Clarification Handling:

    When tool returns clarification:
        1. Build clarification message from result.clarification
           Example: "Which Miami do you mean: Port of Miami or Miami Container Terminal?"
        2. Set state["agent_response"] = clarification_message
        3. Save memory entry (turn_id incremented for clarification)
        4. END TURN with current_phase="clarification"
        5. Next turn: user answers → classify_intent → determines if exact_answer/modification

    Moving Pointer:

    After task completion:
        1. Add current_task_key to completed_tasks list
        2. Find next pending task in tasks dict
        3. Set current_task_key to next task or None if all done

    Query Metadata Creation:

    When all TODOs complete (especially after executor):
        query_metadata = {
            "query_type": "elasticsearch",
            "query_structure": {
                "filters": extract_filters(state["query"]),
                "time_range": state["intent"]["time_range"],
                "fields": extract_fields(state["resolution"])
            },
            "result_summary": f"Found {record_count} records",
            "how_to_retrieve": {
                "index": state["query"]["es_query"]["index"],
                "query": state["query"]["es_query"]["query"]
            },
            "record_count": state["execution"]["record_count"],
            "data_source": "elasticsearch"
        }

    Example Scenarios:

    Scenario 1: Successful Execution (No Clarification)
        Task: "resolve_entities"
        Tool: entity_resolution
        Result: All entities resolved with high confidence
        Action: Mark complete, move to "map_fields", continue loop

    Scenario 2: Clarification Needed
        Task: "resolve_entities"
        Tool: entity_resolution
        Result: Ambiguous entity "Miami" (2 matches)
        Action: Ask user "Which Miami?", save memory, END TURN

    Scenario 3: Error During Execution
        Task: "execute_query"
        Tool: es_executor
        Result: Connection timeout
        Action: Set error, report to user, save memory, END TURN

    Scenario 4: All TODOs Complete
        Task: "execute_query" (last task)
        Tool: es_executor
        Result: 42 records returned
        Action: Build final response, save query_metadata, END TURN

    Implementation Notes:
        - Each TODO execution creates 1 ConversationTurn
        - Memory saved immediately after each task
        - Pointer movement is deterministic (next pending task)
        - YOLO mode: Skip clarification if brutal_force=True
        - Increment iteration_count to prevent infinite loops

    Error Handling:
        - Tool not found: Report error, don't fail entire turn
        - Tool execution error: Capture in ToolResult.error, report to user
        - State corruption: Validate before execution, fail gracefully

    Performance:
        - Each tool call may take 1-5 seconds
        - LLM tools slower than traditional tools
        - Consider timeout handling for long-running queries

    Raises:
        Should NOT raise - return error in state instead
    """
    # TODO: Get current task from TODO list
    # active_todo_list = state.get("active_todo_list")
    # if not active_todo_list:
    #     return {
    #         "error": "No active TODO list",
    #         "current_phase": "error"
    #     }

    # current_task_key = active_todo_list["current_task_key"]
    # if not current_task_key:
    #     # All TODOs complete
    #     return handle_all_todos_complete(state)

    # task = active_todo_list["tasks"][current_task_key]

    # TODO: Mark task as in_progress
    # task["status"] = "in_progress"

    # TODO: Execute tool
    # tool_name = task["tool"]
    # params = task["params"]
    # result = registry.execute(tool_name, **params)

    # TODO: Handle result based on success/clarification/error
    # if not result.success:
    #     # Error case
    #     return handle_tool_error(state, task, result)

    # if result.clarification:
    #     # Clarification needed
    #     return handle_clarification_needed(state, task, result)

    # # Success case
    # return handle_tool_success(state, task, result, registry)

    raise NotImplementedError("Implement TODO execution logic")


def handle_tool_success(
    state: BIAgentState,
    task: dict,
    result: "ToolResult",
    registry: ToolRegistry
) -> dict:
    """
    Handle successful tool execution.

    Args:
        state: Current state
        task: Executed task
        result: Tool result
        registry: Tool registry

    Returns:
        State updates

    Implementation Notes:
        - Mark task complete
        - Update appropriate context (resolution/query/execution)
        - Save memory
        - Move pointer to next task
        - Return state updates for loop continuation
    """
    # TODO: Implement success handling
    raise NotImplementedError("Handle tool success")


def handle_clarification_needed(
    state: BIAgentState,
    task: dict,
    result: "ToolResult"
) -> dict:
    """
    Handle clarification request from tool.

    Args:
        state: Current state
        task: Executed task
        result: Tool result with clarification

    Returns:
        State updates with agent_response and END TURN

    Implementation Notes:
        - Build clarification message from result.clarification
        - Set agent_response
        - Save memory entry
        - END TURN (current_phase="clarification")
    """
    # TODO: Implement clarification handling
    raise NotImplementedError("Handle clarification")


def handle_tool_error(
    state: BIAgentState,
    task: dict,
    result: "ToolResult"
) -> dict:
    """
    Handle tool execution error.

    Args:
        state: Current state
        task: Failed task
        result: Tool result with error

    Returns:
        State updates with error and END TURN

    Implementation Notes:
        - Build error message
        - Set error in state
        - Set agent_response
        - Save memory entry
        - END TURN (current_phase="error")
    """
    # TODO: Implement error handling
    raise NotImplementedError("Handle tool error")


def handle_all_todos_complete(state: BIAgentState) -> dict:
    """
    Handle completion of all TODOs.

    Args:
        state: Current state with completed TODOs

    Returns:
        State updates with final response

    Implementation Notes:
        - Extract query results from execution context
        - Build query_metadata for future analysis
        - Format final response
        - Save final memory entry
        - Return with current_phase="format_response"
    """
    # TODO: Implement completion handling
    raise NotImplementedError("Handle all TODOs complete")


def move_todo_pointer(active_todo_list: dict, completed_task_key: str) -> str | None:
    """
    Move TODO pointer to next pending task.

    Args:
        active_todo_list: TodoListContext
        completed_task_key: Just completed task

    Returns:
        Next task key or None if all done

    Implementation Notes:
        - Add completed_task_key to completed_tasks list
        - Find first task with status="pending"
        - Return its key or None
    """
    # TODO: Implement pointer movement
    raise NotImplementedError("Move TODO pointer")


def save_memory_entry(
    state: BIAgentState,
    task: dict,
    result: "ToolResult",
    agent_response: str
) -> None:
    """
    Save conversation turn to memory.

    Args:
        state: Current state
        task: Executed task
        result: Tool result
        agent_response: Agent's response text

    Implementation Notes:
        - Create ConversationTurn with all context
        - Add to short-term memory
        - Persist to long-term memory (async)
        - Increment turn counter
    """
    # TODO: Implement memory saving
    raise NotImplementedError("Save memory entry")


def build_query_metadata(state: BIAgentState) -> dict:
    """
    Build query metadata for future analysis.

    Args:
        state: State with execution results

    Returns:
        QueryMetadata dict

    Implementation Notes:
        - Extract query structure from query context
        - Extract result summary from execution context
        - Build how_to_retrieve with full query
        - Include record count, data source
    """
    # TODO: Implement metadata builder
    raise NotImplementedError("Build query metadata")


def format_final_response(state: BIAgentState) -> str:
    """
    Format final response for user.

    Args:
        state: State with execution results

    Returns:
        Formatted response string

    Implementation Notes:
        - Extract results from execution context
        - Format as user-friendly text
        - Include count, highlights
        - Keep concise
    """
    # TODO: Implement response formatter
    raise NotImplementedError("Format final response")
