"""Result-based routing for TODO execution.

Routes from execute_next_todo based on execution outcome.
"""

from domain.state import BIAgentState
from typing import Literal


def route_after_execution(
    state: BIAgentState
) -> Literal["execute_next_todo", "clarification", "format_response", "error"]:
    """
    Route based on TODO execution result.

    Routing Logic:
        1. Success + More TODOs → execute_next_todo (loop back)
        2. Success + All done → format_response (end turn)
        3. Clarification needed → clarification (end turn, ask user)
        4. Error → error (end turn, report error)

    Args:
        state: Current agent state after TODO execution

    Returns:
        Next node name:
            - "execute_next_todo": Continue with next task
            - "format_response": All TODOs complete, format final response
            - "clarification": Tool needs user input
            - "error": Tool execution failed

    Implementation Notes:
        - Check if current_phase set to "clarification" or "error" by execute_next_todo
        - Check if active_todo_list.current_task_key is None (all done)
        - Otherwise, loop back to execute_next_todo

    Routing Table:
        current_phase="clarification" → clarification (END TURN)
        current_phase="error"         → error (END TURN)
        current_task_key=None         → format_response (all TODOs done)
        current_task_key exists       → execute_next_todo (continue loop)

    Example Scenarios:

    Scenario 1: Task Complete, More TODOs Remain
        State: current_phase="execute_next_todo", current_task_key="map_fields"
        Route: → execute_next_todo (loop back)

    Scenario 2: Task Needs Clarification
        State: current_phase="clarification", agent_response="Which Miami?"
        Route: → clarification (END TURN, ask user)

    Scenario 3: All TODOs Complete
        State: current_phase="execute_next_todo", current_task_key=None
        Route: → format_response (format final response)

    Scenario 4: Task Failed with Error
        State: current_phase="error", error="Connection timeout"
        Route: → error (END TURN, report error)

    Loop Control:
        - execute_next_todo node increments iteration_count
        - If iteration_count > MAX_ITERATIONS, force exit to avoid infinite loop
        - This router enables the cyclic TODO execution pattern

    Clarification Handling:
        - When tool returns clarification, execute_next_todo sets:
            - current_phase="clarification"
            - agent_response="clarification question"
        - This router sends to clarification node
        - Turn ends, user responds
        - Next turn: classify_intent → determines if exact_answer/modification

    Error Handling:
        - When tool fails, execute_next_todo sets:
            - current_phase="error"
            - error="error message"
            - agent_response="user-friendly error"
        - This router sends to error node
        - Turn ends with error response

    Raises:
        Should NOT raise - return "error" node if routing unclear
    """
    # TODO: Extract current phase
    # current_phase = state.get("current_phase")

    # TODO: Check for clarification or error
    # if current_phase == "clarification":
    #     return "clarification"
    # if current_phase == "error" or state.get("error"):
    #     return "error"

    # TODO: Check if all TODOs complete
    # active_todo_list = state.get("active_todo_list", {})
    # current_task_key = active_todo_list.get("current_task_key")

    # if current_task_key is None:
    #     # All TODOs done
    #     return "format_response"

    # TODO: More TODOs remain, loop back
    # return "execute_next_todo"

    raise NotImplementedError("Implement result routing logic")


def route_after_response(state: BIAgentState) -> Literal["END"]:
    """
    Route after response formatting.

    Always ends the turn after final response formatted.

    Args:
        state: State with formatted agent_response

    Returns:
        "END": Always end turn

    Implementation Notes:
        - Called after format_response node
        - Always returns "END" to complete turn
        - LangGraph END constant terminates turn execution
    """
    return "END"
