"""Reiterate user intention as clean, unambiguous question.

Cleans up user input for better query processing.
Only runs for new_request or modification intents.
"""

from domain.state import BIAgentState
from tools.registry import ToolRegistry


def reiterate_intention(state: BIAgentState, registry: ToolRegistry) -> dict:
    """
    Rewrite user question as clean, unambiguous statement.

    Takes raw user input and rewrites it as a clear question suitable for:
    - TODO planning
    - Entity extraction
    - Query construction

    Purpose:
        - Remove ambiguity ("that", "it", "last one")
        - Expand abbreviations ("LA" → "Los Angeles")
        - Normalize phrasing ("gimme" → "show me")
        - Preserve semantic meaning exactly

    Args:
        state: Current agent state with:
            - user_input: Raw user message
            - intent: IntentContext with entities/time_range
            - memory: ShortTermMemory for context resolution
        registry: Tool registry for LLM calls

    Returns:
        State updates:
            {
                "intent": {
                    ...existing intent fields,
                    "rewritten_question": "Show all shipments to Port of Miami in last 7 days"
                },
                "current_phase": "reiterate_intention"
            }

    State Updates:
        - intent.rewritten_question: Clean question
        - current_phase: "reiterate_intention"

    Implementation Flow:
        1. Extract user_input and intent context
        2. Get short-term memory for pronoun resolution
           Example: If user says "show me arrivals there", need previous context
        3. Build rewrite prompt with:
           - user_input
           - context from memory (for pronoun resolution)
           - already extracted entities/time_range (from classify_intent)
        4. Call LLM to rewrite
        5. Update intent.rewritten_question
        6. Return state updates

    Example Rewrites:

    Example 1: Pronoun Resolution
        Input: "Show me shipments there last week"
        Context: Previous turn mentioned "Port of Miami"
        Output: "Show all shipments to Port of Miami in last 7 days"

    Example 2: Abbreviation Expansion
        Input: "Gimme vessels in LA port"
        Output: "Show all vessels in Los Angeles port"

    Example 3: Ambiguity Removal
        Input: "What about that vessel yesterday?"
        Context: Previous turn discussed "MSC ANNA"
        Output: "Show information about vessel MSC ANNA yesterday"

    Example 4: Normalization
        Input: "i wanna see stuff for miami"
        Output: "Show all records for Miami"

    Example 5: Already Clean (No Change)
        Input: "Show all shipments to Port of Miami in last 7 days"
        Output: "Show all shipments to Port of Miami in last 7 days" (unchanged)

    Implementation Notes:
        - Use llm_tool for rewriting
        - Include context from memory for pronoun resolution
        - Use entities already extracted by classify_intent
        - Keep rewrite concise and clear
        - Preserve all semantic information
        - Don't add information not in input or context

    Prompt Template (Pseudocode):
        ```
        Rewrite this user question as a clear, unambiguous statement.

        Original: "{user_input}"

        Context from conversation:
        {short_term_memory_context}

        Extracted entities: {entities}
        Time range: {time_range}

        Rules:
        1. Resolve pronouns (it, that, there) using context
        2. Expand abbreviations
        3. Use clear, formal language
        4. Preserve exact meaning
        5. Don't add information not present
        6. If already clear, return as-is

        Return only the rewritten question.
        ```

    Error Handling:
        - If LLM fails, use original user_input as fallback
        - If rewrite is empty, use original user_input
        - If rewrite changes meaning significantly, log warning and use original

    Validation:
        - Check rewritten question not empty
        - Check entities from original still present
        - Check no hallucinated information added

    Performance Optimization:
        - If user_input already clean (formal, no pronouns), skip LLM call
        - Cache common rewrites (rare, but possible)

    Raises:
        Should NOT raise - return error in state instead
    """
    # TODO: Extract user input and intent
    # user_input = state["user_input"]
    # intent = state.get("intent", {})
    # memory = state.get("memory")

    # TODO: Get context for pronoun resolution
    # context = memory.get_recent_context(n=2) if memory else ""

    # TODO: Check if rewrite needed
    # if is_already_clean(user_input):
    #     return {
    #         "intent": {**intent, "rewritten_question": user_input},
    #         "current_phase": "reiterate_intention"
    #     }

    # TODO: Build rewrite prompt
    # prompt = build_rewrite_prompt(
    #     user_input=user_input,
    #     context=context,
    #     entities=intent.get("entities", {}),
    #     time_range=intent.get("time_range")
    # )

    # TODO: Call LLM
    # result = registry.execute(
    #     "llm_tool",
    #     prompt=prompt,
    #     temperature=0.1  # Low temp for consistent rewrites
    # )

    # TODO: Validate and use rewrite
    # if result.success and result.data:
    #     rewritten = result.data.strip()
    #     if validate_rewrite(original=user_input, rewritten=rewritten, entities=intent.get("entities")):
    #         rewritten_question = rewritten
    #     else:
    #         rewritten_question = user_input  # Fallback to original
    # else:
    #     rewritten_question = user_input  # Fallback to original

    # TODO: Update intent with rewritten question
    # updated_intent = {**intent, "rewritten_question": rewritten_question}

    # TODO: Return state updates
    # return {
    #     "intent": updated_intent,
    #     "current_phase": "reiterate_intention"
    # }

    raise NotImplementedError("Implement intention reiteration logic")


def is_already_clean(user_input: str) -> bool:
    """
    Check if user input is already clean and doesn't need rewriting.

    Args:
        user_input: User's message

    Returns:
        True if already clean, False if needs rewriting

    Implementation Notes:
        - Check for pronouns (it, that, there, this)
        - Check for abbreviations (LA, NY, etc.)
        - Check for informal language (gimme, wanna)
        - If formal and complete, return True
    """
    # TODO: Implement cleanliness check
    # Check for common pronouns: it, that, there, this
    # Check for informal words: gimme, wanna, gonna
    # If none found, likely already clean
    raise NotImplementedError("Check if input already clean")


def build_rewrite_prompt(
    user_input: str,
    context: str,
    entities: dict,
    time_range: dict | None
) -> str:
    """
    Build rewrite prompt for LLM.

    Args:
        user_input: Original user message
        context: Short-term memory context
        entities: Extracted entities
        time_range: Extracted time range

    Returns:
        Formatted prompt for LLM

    Implementation Notes:
        - Include context for pronoun resolution
        - Show entities already extracted
        - Emphasize preserving meaning
        - Include few-shot examples
    """
    # TODO: Build prompt with examples
    raise NotImplementedError("Build rewrite prompt")


def validate_rewrite(original: str, rewritten: str, entities: dict) -> bool:
    """
    Validate rewritten question preserves meaning.

    Args:
        original: Original user input
        rewritten: Rewritten question
        entities: Extracted entities from original

    Returns:
        True if rewrite is valid, False if should use original

    Implementation Notes:
        - Check rewritten not empty
        - Check key entities still present
        - Check not too different (semantic drift)
        - Use fuzzy matching for entity names
    """
    # TODO: Implement validation logic
    # Check rewritten not empty
    # Check entities still mentioned
    # Check not hallucinated information
    raise NotImplementedError("Validate rewrite")
