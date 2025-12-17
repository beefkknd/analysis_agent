"""Classify user intent and check TODO list validity.

This is the entry point for every conversation turn in the cyclic flow.
LLM-based classification determines routing to next action.
"""

from domain.state import BIAgentState, IntentContext
from tools.registry import ToolRegistry
from typing import Literal


def classify_intent(state: BIAgentState, registry: ToolRegistry) -> dict:
    """
    Classify user intent and check TODO list validity.

    This node is the entry point for EVERY turn in the cyclic flow.
    Uses LLM to analyze user input in context of:
    - Short-term memory (last N turns)
    - Active TODO list (if exists)
    - Semantic meaning of user response

    Classification Routes:
        1. new_request: New task, ditch existing TODO list
           Example: "Show me shipments to Miami"
           Action: → reiterate_intention → plan_todos

        2. exact_answer: Direct answer to clarification, rerun same TODO
           Example: Agent asked "Which Miami?", user says "Port of Miami" (exact)
           Action: → execute_next_todo (rerun current task_key)

        3. modification: Answer + new requirements, replan TODO list
           Example: Agent asked "Which Miami?", user says "Port of Miami, but also add arrival date"
           Action: → reiterate_intention → plan_todos (ditch old TODO list)

        4. continuation: User says "continue" or similar
           Example: "yes, continue", "go ahead"
           Action: → execute_next_todo (move to next task)

    Args:
        state: Current agent state with:
            - user_input: User's message
            - active_todo_list: Current TODO list (if exists)
            - memory: ShortTermMemory reference
        registry: Tool registry for LLM calls

    Returns:
        State updates with populated IntentContext:
            {
                "intent": {
                    "intent_type": "new_request" | "exact_answer" | "modification" | "continuation",
                    "confidence": 0.0-1.0,
                    "todo_list_valid": bool,
                    "entities": {...},
                    "aggregation_keywords": [...],
                    "time_range": {...} | None,
                    "requires_clarification": [...],
                    "rewritten_question": str | None
                },
                "current_phase": "classify_intent"
            }

    State Updates:
        - intent: IntentContext with classification results
        - current_phase: "classify_intent"

    Implementation Flow:
        1. Check if active_todo_list exists in state
        2. Get short-term memory context (last N turns)
        3. Build classification prompt with:
           - user_input
           - short_term_memory context
           - active_todo_list (if exists)
           - last TODO context (what was being worked on)
        4. Call LLM with structured output schema (IntentContext)
        5. Parse LLM response:
           - intent_type: Which route to take
           - todo_list_valid: Is current TODO list still valid?
           - entities: Extracted entity mentions
           - requires_clarification: What needs clarification (if any)
        6. Return state updates

    Classification Logic:
        - If no active_todo_list exists → new_request
        - If active_todo_list exists:
            - Check semantic meaning of user_input
            - Compare with last TODO context
            - Determine: exact_answer, modification, or continuation

    Example Scenarios:

    Scenario 1: New Request (No active TODO list)
        State: active_todo_list = None
        Input: "Show shipments to Miami last week"
        Output: intent_type="new_request", entities={"port": ["Miami"]}, time_range={...}

    Scenario 2: Exact Answer (Agent asked clarification)
        State: active_todo_list exists, current_task_key="resolve_entities"
        Last turn: Agent asked "Which Miami: Port of Miami or Miami Container Terminal?"
        Input: "Port of Miami"
        Output: intent_type="exact_answer", todo_list_valid=True

    Scenario 3: Modification (Answer + new requirement)
        State: active_todo_list exists, current_task_key="resolve_entities"
        Last turn: Agent asked "Which Miami?"
        Input: "Port of Miami, but also include arrival date last week"
        Output: intent_type="modification", todo_list_valid=False, entities={"port": ["Port of Miami"]}, time_range={...}

    Scenario 4: Abort (User changes topic mid-flow)
        State: active_todo_list exists, 3 of 5 TODOs completed
        Input: "Forget that, show me vessels in Shanghai"
        Output: intent_type="new_request", todo_list_valid=False, entities={"port": ["Shanghai"]}

    Scenario 5: Continuation
        State: active_todo_list exists, waiting for user approval
        Input: "yes, continue" or "go ahead"
        Output: intent_type="continuation", todo_list_valid=True

    Implementation Notes:
        - Use llm_tool with structured output (JSON schema for IntentContext)
        - Prompt should include examples for each intent_type
        - LLM should analyze semantic meaning, not just keywords
        - If todo_list_valid=False, active_todo_list will be ditched in routing
        - Extract entities and time ranges even if not new_request (may need for replanning)
        - confidence score helps with uncertain classifications

    Error Handling:
        - If LLM call fails, return error state (will trigger error handling node)
        - If classification uncertain (confidence < 0.6), log warning but proceed
        - Default to new_request if unable to determine

    Prompt Template (Pseudocode):
        ```
        You are analyzing user intent for a BI agent.

        User input: "{user_input}"

        Recent conversation:
        {short_term_memory_context}

        Active TODO list:
        {active_todo_list_summary}

        Current task: {current_task_description}

        Classify the user intent:
        1. new_request: New task, abandon current TODO list
        2. exact_answer: Direct answer to last question (no new info)
        3. modification: Answer + new requirements (need to replan)
        4. continuation: User wants to continue current plan

        Extract:
        - Entities mentioned (vessel, port, terminal, etc.)
        - Time ranges (last week, 2024-01-01, etc.)
        - Aggregation keywords (latest, average, count, etc.)

        Return JSON matching IntentContext schema.
        ```

    Raises:
        Should NOT raise - return error in state instead
    """
    # TODO: Extract user input and current state
    # user_input = state["user_input"]
    # active_todo_list = state.get("active_todo_list")
    # memory = state.get("memory")

    # TODO: Get short-term memory context
    # context = memory.get_recent_context(n=3) if memory else ""

    # TODO: Build classification prompt
    # prompt = build_classification_prompt(
    #     user_input=user_input,
    #     context=context,
    #     active_todo_list=active_todo_list
    # )

    # TODO: Call LLM with structured output
    # result = registry.execute(
    #     "llm_tool",
    #     prompt=prompt,
    #     output_schema=IntentContext.__annotations__,
    #     temperature=0.1  # Low temperature for consistent classification
    # )

    # TODO: Parse LLM response into IntentContext
    # if result.success:
    #     intent_data = result.data
    #     intent_context = IntentContext(**intent_data)
    # else:
    #     # Handle error - default to new_request
    #     intent_context = IntentContext(
    #         intent_type="new_request",
    #         confidence=0.5,
    #         todo_list_valid=False,
    #         entities={},
    #         aggregation_keywords=[],
    #         requires_clarification=[]
    #     )

    # TODO: Return state updates
    # return {
    #     "intent": intent_context,
    #     "current_phase": "classify_intent"
    # }

    raise NotImplementedError("Implement intent classification logic")


def build_classification_prompt(
    user_input: str,
    context: str,
    active_todo_list: dict | None
) -> str:
    """
    Build classification prompt for LLM.

    Args:
        user_input: Current user message
        context: Short-term memory context
        active_todo_list: Active TODO list (if exists)

    Returns:
        Formatted prompt for LLM

    Implementation Notes:
        - Include few-shot examples for each intent_type
        - Format active_todo_list summary clearly
        - Emphasize semantic analysis over keyword matching
    """
    # TODO: Build prompt with examples
    raise NotImplementedError("Build classification prompt")


def determine_todo_validity(
    user_input: str,
    active_todo_list: dict,
    llm_response: dict
) -> bool:
    """
    Determine if active TODO list is still valid.

    Args:
        user_input: User's message
        active_todo_list: Current TODO list
        llm_response: LLM classification response

    Returns:
        True if TODO list valid, False if should be ditched

    Implementation Notes:
        - Called by LLM or as post-processing
        - Check if user introduced new entities/requirements
        - Check if user explicitly aborted ("forget that", "nevermind")
        - Check if user answered exact question asked
    """
    # TODO: Implement validity logic
    raise NotImplementedError("Determine TODO validity")
