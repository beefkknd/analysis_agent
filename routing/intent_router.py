"""Intent-based routing for cyclic flow.

Routes from classify_intent node based on intent_type and TODO list validity.
"""

from domain.state import BIAgentState
from typing import Literal


def route_after_intent(state: BIAgentState) -> Literal["reiterate_intention", "execute_next_todo", "error"]:
    """
    Route based on intent classification results.

    Routing Logic:
        1. new_request → reiterate_intention (then plan_todos)
        2. modification → reiterate_intention (ditch old TODO list, replan)
        3. exact_answer → execute_next_todo (rerun current task)
        4. continuation → execute_next_todo (move to next task)

    Args:
        state: Current agent state with populated intent context

    Returns:
        Next node name:
            - "reiterate_intention": New request or modification
            - "execute_next_todo": Exact answer or continuation
            - "error": Classification failed

    Implementation Notes:
        - Check intent.intent_type for routing decision
        - If intent_type is "new_request" or "modification" → reiterate_intention
        - If intent_type is "exact_answer" or "continuation" → execute_next_todo
        - If no intent or error → "error"

    Routing Table:
        intent_type="new_request"     → reiterate_intention → plan_todos → execute_next_todo
        intent_type="modification"    → reiterate_intention → plan_todos → execute_next_todo
        intent_type="exact_answer"    → execute_next_todo (rerun current task)
        intent_type="continuation"    → execute_next_todo (next task)
        intent_type missing           → error

    Example Scenarios:

    Scenario 1: New Request
        State: intent.intent_type = "new_request"
        Route: → reiterate_intention

    Scenario 2: User Modifies Request
        State: intent.intent_type = "modification", todo_list_valid = False
        Route: → reiterate_intention (will replan)

    Scenario 3: User Answers Exact Question
        State: intent.intent_type = "exact_answer", todo_list_valid = True
        Route: → execute_next_todo (rerun current task with answer)

    Scenario 4: User Continues
        State: intent.intent_type = "continuation"
        Route: → execute_next_todo (move to next task)

    Edge Cases:
        - If todo_list_valid=False but intent_type="exact_answer":
            Should not happen (LLM error), default to reiterate_intention
        - If no active_todo_list but intent_type="continuation":
            Should not happen, default to reiterate_intention

    Raises:
        Should NOT raise - return "error" node if routing unclear
    """
    # TODO: Extract intent from state
    # intent = state.get("intent", {})
    # intent_type = intent.get("intent_type")

    # TODO: Validate intent_type present
    # if not intent_type:
    #     return "error"

    # TODO: Route based on intent_type
    # if intent_type in ["new_request", "modification"]:
    #     return "reiterate_intention"
    # elif intent_type in ["exact_answer", "continuation"]:
    #     return "execute_next_todo"
    # else:
    #     # Unknown intent_type, error
    #     return "error"

    raise NotImplementedError("Implement intent routing logic")
