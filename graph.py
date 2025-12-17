"""LangGraph assembly for cyclic TODO-based flow.

Assembles the agent graph with cyclic execution pattern:
    classify_intent → route → execute_next_todo → route → loop or END
"""

from langgraph.graph import StateGraph, END
from domain.state import BIAgentState
from tools.registry import ToolRegistry
from config.settings import Settings

# Import nodes
from nodes.classify_intent import classify_intent
from nodes.reiterate_intention import reiterate_intention
from nodes.plan_todos import plan_todos
from nodes.execute_next_todo import execute_next_todo

# Import routing
from routing.intent_router import route_after_intent
from routing.result_router import route_after_execution, route_after_response


def create_bi_graph(
    tool_registry: ToolRegistry,
    settings: Settings,
    checkpointer
):
    """
    Create and compile the BI agent graph with cyclic TODO execution.

    Graph Flow:
        ┌─────────────────┐
        │  START (turn)   │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ classify_intent │  ← Entry point (every turn starts here)
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │  Route Intent   │  (Conditional edge)
        └────────┬────────┘
                 │
         ┌───────┴────────┐
         │                │
    ┌────▼────┐    ┌──────▼──────┐
    │ reiterate│    │execute_next │
    │intention │    │   _todo     │
    └────┬────┘    └──────┬──────┘
         │                │
    ┌────▼────┐    ┌──────▼──────┐
    │ plan_   │    │Route Result │ (Conditional edge)
    │ todos   │    └──────┬──────┘
    └────┬────┘           │
         │          ┌─────┴─────┬──────────┬──────────┐
         │          │           │          │          │
         └──────────▶execute   clarify  format    error
                    next_todo    │      response     │
                       │         │         │         │
                       └─────────┴─────────┴─────────▶ END

    Key Features:
        - Every turn starts at classify_intent (cyclic entry)
        - execute_next_todo loops back to itself via routing
        - Clarification ends turn, next turn restarts at classify_intent
        - Error handling integrated into routing

    Args:
        tool_registry: Registry with all tools
        settings: Application settings (for YOLO mode, etc.)
        checkpointer: LangGraph checkpointer for state persistence

    Returns:
        Compiled LangGraph instance

    Implementation Notes:
        - BIAgentState flows through all nodes
        - Each node returns dict with state updates
        - Conditional edges use routing functions
        - Nodes use tool_registry.execute() for tool calls
        - Memory managed by agent.py (not graph)
    """

    # Create graph with state schema
    graph = StateGraph(BIAgentState)

    # === ADD NODES ===

    # Core nodes (4 nodes for cyclic flow)
    graph.add_node(
        "classify_intent",
        lambda state: classify_intent(state, tool_registry)
    )

    graph.add_node(
        "reiterate_intention",
        lambda state: reiterate_intention(state, tool_registry)
    )

    graph.add_node(
        "plan_todos",
        lambda state: plan_todos(state, tool_registry)
    )

    graph.add_node(
        "execute_next_todo",
        lambda state: execute_next_todo(state, tool_registry)
    )

    # Response nodes (for clarification and final response)
    graph.add_node(
        "format_response",
        lambda state: format_final_response(state, tool_registry)
    )

    graph.add_node(
        "clarification",
        lambda state: handle_clarification(state)
    )

    graph.add_node(
        "error",
        lambda state: handle_error(state)
    )

    # === ADD EDGES ===

    # Entry point: Every turn starts here
    graph.set_entry_point("classify_intent")

    # classify_intent → Route by intent_type
    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {
            "reiterate_intention": "reiterate_intention",  # new_request or modification
            "execute_next_todo": "execute_next_todo",      # exact_answer or continuation
            "error": "error"                               # classification failed
        }
    )

    # reiterate_intention → plan_todos (always)
    graph.add_edge("reiterate_intention", "plan_todos")

    # plan_todos → execute_next_todo (always)
    graph.add_edge("plan_todos", "execute_next_todo")

    # execute_next_todo → Route by result
    graph.add_conditional_edges(
        "execute_next_todo",
        route_after_execution,
        {
            "execute_next_todo": "execute_next_todo",  # Loop back (more TODOs)
            "format_response": "format_response",       # All TODOs done
            "clarification": "clarification",           # Tool needs user input
            "error": "error"                            # Tool failed
        }
    )

    # Terminal nodes (end turn)
    graph.add_edge("format_response", END)
    graph.add_edge("clarification", END)
    graph.add_edge("error", END)

    # Compile and return
    return graph.compile(checkpointer=checkpointer)


# === Helper Nodes ===

def format_final_response(state: BIAgentState, registry: ToolRegistry) -> dict:
    """
    Format final response after all TODOs complete.

    Args:
        state: State with execution results
        registry: Tool registry

    Returns:
        State updates with agent_response

    Implementation Notes:
        - Extract results from execution context
        - Format as user-friendly text
        - Save query_metadata for future analysis
        - Set agent_response
    """
    # TODO: Extract results
    # execution = state.get("execution", {})
    # record_count = execution.get("record_count", 0)
    # raw_results = execution.get("raw_results", {})

    # TODO: Format response
    # response = f"Found {record_count} records. ..."

    # TODO: Build query_metadata
    # query_metadata = build_query_metadata(state)

    # TODO: Return state updates
    # return {
    #     "agent_response": response,
    #     "execution": {
    #         **execution,
    #         "query_metadata": query_metadata
    #     },
    #     "current_phase": "format_response"
    # }

    raise NotImplementedError("Implement response formatting")


def handle_clarification(state: BIAgentState) -> dict:
    """
    Handle clarification turn end.

    Args:
        state: State with clarification question in agent_response

    Returns:
        State updates (agent_response already set by execute_next_todo)

    Implementation Notes:
        - agent_response already set by execute_next_todo
        - Just return state as-is
        - Turn ends, user responds
        - Next turn: classify_intent determines if exact_answer/modification
    """
    return {"current_phase": "clarification"}


def handle_error(state: BIAgentState) -> dict:
    """
    Handle error turn end.

    Args:
        state: State with error message

    Returns:
        State updates with user-friendly error in agent_response

    Implementation Notes:
        - error field set by classify_intent or execute_next_todo
        - Convert to user-friendly message
        - Set agent_response
        - Turn ends
    """
    # TODO: Extract error
    # error = state.get("error", "An unknown error occurred")

    # TODO: Build user-friendly message
    # agent_response = f"I encountered an error: {error}. Please try again."

    # TODO: Return state updates
    # return {
    #     "agent_response": agent_response,
    #     "current_phase": "error"
    # }

    raise NotImplementedError("Implement error handling")


def build_query_metadata(state: BIAgentState) -> dict:
    """
    Build query metadata for future analysis.

    Args:
        state: State with query and execution results

    Returns:
        QueryMetadata dict

    Implementation Notes:
        - Extract query structure from query context
        - Extract result summary from execution context
        - Build how_to_retrieve with full query
        - Include record count, data source
        - Used by "analyze X" follow-up requests
    """
    # TODO: Implement metadata builder
    # See domain/query.py QueryMetadata for structure
    raise NotImplementedError("Build query metadata")
