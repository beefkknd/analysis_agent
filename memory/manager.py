"""Memory manager for conversation turns.

In new architecture, 1 ConversationTurn = 1 TODO execution (not 1 user request).
MemoryManager handles memory creation and context injection.
"""

from datetime import datetime
from domain.conversation import ConversationTurn, Message
from domain.memory import ShortTermMemory
from domain.state import BIAgentState


class MemoryManager:
    """
    Manages memory across conversation turns.

    IMPORTANT: In new architecture, 1 turn = 1 TODO completion.
    If 5 TODOs execute, 5 ConversationTurns are created.

    Responsibilities:
        - Initialize state at start of turn
        - Create ConversationTurn after each TODO execution
        - Inject short-term memory context into prompts
        - Track TODO-level conversation history

    Architecture:
        Checkpoint (LangGraph) = Within-turn state persistence
        Memory (MemoryManager) = Cross-turn conversation history

    Attributes:
        short_term: ShortTermMemory instance (last N turns)
        turn_counter: Global turn counter across conversation

    Usage:
        # At start of user request
        state = manager.start_turn(turn_id=1, user_input="Show shipments...")

        # After each TODO execution
        turn = manager.save_todo_completion(state, task_result)

        # Get context for prompts
        context = manager.get_context_for_prompt(n_turns=3)
    """

    def __init__(self, short_term_memory: ShortTermMemory):
        """
        Initialize memory manager.

        Args:
            short_term_memory: ShortTermMemory instance

        Implementation Notes:
            - Short-term memory shared across all turns
            - Turn counter managed externally by BIAgent
        """
        self.short_term = short_term_memory

    def start_turn(self, turn_id: int, user_input: str) -> BIAgentState:
        """
        Initialize state for a new turn.

        Called at the beginning of each user request (not each TODO).
        Injects short-term memory context.

        Args:
            turn_id: Sequential turn number
            user_input: User's message for this turn

        Returns:
            Initial BIAgentState for graph execution

        Implementation Notes:
            - memory reference injected (not serialized by checkpointer)
            - current_turn_id used for tracking
            - iteration_count starts at 0
            - All contexts start empty
            - active_todo_list preserved if exists (for continuation)

        Example:
            state = manager.start_turn(turn_id=5, user_input="Port of Miami")
            # State ready for graph.invoke()
        """
        # TODO: Build initial state
        # return {
        #     "messages": [],
        #     "current_turn_id": turn_id,
        #     "user_input": user_input,
        #     "memory": self.short_term,  # Reference for nodes to access
        #     "current_phase": "classify_intent",
        #     "iteration_count": 0,
        #     "intent": {},
        #     "active_todo_list": None,  # Will be set by plan_todos
        #     "resolution": {},
        #     "query": {},
        #     "execution": {},
        #     "error": None,
        #     "agent_response": None
        # }

        raise NotImplementedError("Initialize turn state")

    def save_todo_completion(
        self,
        state: BIAgentState,
        task_key: str,
        task_result: dict,
        agent_response_text: str
    ) -> ConversationTurn:
        """
        Save conversation turn after TODO completion.

        IMPORTANT: Called after EACH TODO execution, not just final response.
        This creates the detailed conversation history (1 entry per TODO).

        Args:
            state: Current agent state
            task_key: Completed task key (e.g., "resolve_entities")
            task_result: ToolResult from task execution
            agent_response_text: Agent's response (result, clarification, or error)

        Returns:
            ConversationTurn object (added to short-term memory)

        Implementation Notes:
            - Extract relevant context from state
            - Build ConversationTurn with all metadata
            - Add to short-term memory
            - Return for long-term memory persistence (by agent.py)

        ConversationTurn Fields:
            - turn_id: Incremented for each TODO
            - user_message: User input (original request or clarification answer)
            - agent_response: Agent's output (result, question, or error)
            - intent_detected: Intent type from classify_intent
            - rewritten_question: Clean question (only for new_request)
            - entities_extracted: Resolved entities
            - queries_executed: List of queries executed in this TODO
            - query_metadata: For future analysis (only when query executed)
            - tokens_used: LLM tokens consumed

        Example:
            # After entity resolution TODO
            turn = manager.save_todo_completion(
                state=state,
                task_key="resolve_entities",
                task_result=result,
                agent_response_text="Resolved vessel to MSC ANNA"
            )
            # turn_id incremented, added to memory

            # After clarification TODO
            turn = manager.save_todo_completion(
                state=state,
                task_key="resolve_entities",
                task_result=result,
                agent_response_text="Which Miami: Port of Miami or Miami Container Terminal?"
            )
            # turn_id incremented, clarification saved
        """
        # TODO: Extract state contexts
        # intent = state.get("intent", {})
        # resolution = state.get("resolution", {})
        # query = state.get("query", {})
        # execution = state.get("execution", {})

        # TODO: Build ConversationTurn
        # turn = ConversationTurn(
        #     turn_id=state["current_turn_id"],
        #     user_message=Message(
        #         role="user",
        #         content=state["user_input"],
        #         timestamp=datetime.now(),
        #         metadata={"task_key": task_key}
        #     ),
        #     agent_response=Message(
        #         role="assistant",
        #         content=agent_response_text,
        #         timestamp=datetime.now(),
        #         metadata={"task_key": task_key, "success": task_result.get("success")}
        #     ),
        #     intent_detected=intent.get("intent_type", "unknown"),
        #     rewritten_question=intent.get("rewritten_question"),
        #     entities_extracted=extract_entities(resolution),
        #     queries_executed=extract_queries(query, execution),
        #     query_metadata=execution.get("query_metadata", {}),
        #     started_at=datetime.now(),
        #     completed_at=datetime.now(),
        #     tokens_used=calculate_tokens(state, task_result)
        # )

        # TODO: Add to short-term memory
        # self.short_term.add_turn(turn)

        # TODO: Return for long-term persistence
        # return turn

        raise NotImplementedError("Save TODO completion")

    def complete_turn(self, state: BIAgentState) -> ConversationTurn:
        """
        Create final turn record after all TODOs complete.

        DEPRECATED in new architecture - use save_todo_completion instead.
        Kept for backward compatibility but should not be used.

        In new flow:
            - save_todo_completion called after EACH TODO
            - No "final turn" concept - last TODO is just another TODO

        Args:
            state: Final state

        Returns:
            ConversationTurn (but prefer save_todo_completion)

        Implementation Notes:
            - This method exists for backward compatibility
            - New code should use save_todo_completion
            - May be removed in future refactor
        """
        # TODO: Implement as fallback
        # Extract contexts and build turn similar to save_todo_completion
        raise NotImplementedError("Use save_todo_completion instead")

    def get_context_for_prompt(self, n_turns: int = 3) -> str:
        """
        Get recent conversation context to inject into prompts.

        This is how the agent "remembers" previous TODOs and clarifications.
        Used by classify_intent and other nodes.

        Args:
            n_turns: Number of recent turns to include (default: 3)
                Each turn = 1 TODO completion

        Returns:
            Formatted context string for prompt injection

        Format Example:
            User: Show shipments to Miami
            Assistant: Which Miami: Port of Miami or Miami Container Terminal?

            User: Port of Miami
            Assistant: Resolved to Port of Miami (USMIAMI1)

            User: Port of Miami, but also add arrival date
            Assistant: Planning new query with arrival date field

        Implementation Notes:
            - Calls short_term.get_recent_context(n)
            - Format is "User: X\nAssistant: Y\n\n"
            - Used in classify_intent to check TODO validity
            - Used in reiterate_intention for pronoun resolution

        Example Usage:
            # In classify_intent node
            context = state["memory"].get_recent_context(n=3)
            prompt = f"Context:\n{context}\n\nUser input: {user_input}\n\nClassify intent..."
        """
        return self.short_term.get_recent_context(n=n_turns)

    def get_last_todo_context(self) -> dict | None:
        """
        Get context from last TODO execution.

        Used by classify_intent to determine if user is answering a clarification.

        Returns:
            Dict with last TODO info or None if no history
            {
                "task_key": "resolve_entities",
                "agent_response": "Which Miami?",
                "was_clarification": True,
                "entities_mentioned": ["Miami"]
            }

        Implementation Notes:
            - Get last turn from short_term memory
            - Extract task_key from metadata
            - Check if was clarification request
            - Used to detect exact_answer vs modification
        """
        # TODO: Get last turn
        # last_turn = self.short_term.get_last_turn()
        # if not last_turn:
        #     return None

        # TODO: Extract context
        # return {
        #     "task_key": last_turn.agent_response.metadata.get("task_key"),
        #     "agent_response": last_turn.agent_response.content,
        #     "was_clarification": "?" in last_turn.agent_response.content,
        #     "entities_mentioned": extract_entities_from_message(last_turn.agent_response.content)
        # }

        raise NotImplementedError("Get last TODO context")

    def clear(self) -> None:
        """
        Clear all conversation memory.

        Called when user explicitly clears conversation or starts fresh.

        Implementation Notes:
            - Clears short-term memory only
            - Long-term memory (vector DB) not affected
            - Turn counter reset externally by BIAgent
        """
        self.short_term.clear()


# === Helper Functions ===

def extract_entities(resolution_context: dict) -> dict:
    """
    Extract entities from resolution context for memory.

    Args:
        resolution_context: ResolutionContext from state

    Returns:
        Dict of entity_type → list of resolved names

    Example:
        {
            "vessel": ["MSC ANNA", "CMA CGM MARCO POLO"],
            "port": ["Port of Miami"]
        }

    Implementation Notes:
        - Parse resolution.resolved_entities
        - Flatten to simple dict format
        - Used in ConversationTurn.entities_extracted
    """
    # TODO: Parse resolution_context["resolved_entities"]
    # Return flattened dict
    raise NotImplementedError("Extract entities")


def extract_queries(query_context: dict, execution_context: dict) -> list[dict]:
    """
    Extract executed queries from contexts for memory.

    Args:
        query_context: QueryContext from state
        execution_context: ExecutionContext from state

    Returns:
        List of query dicts with type, query, summary

    Example:
        [
            {
                "type": "elasticsearch",
                "query": {"query": {"bool": {...}}},
                "summary": "Search shipments by vessel and port",
                "record_count": 42
            }
        ]

    Implementation Notes:
        - Combine query structure with execution results
        - Used in ConversationTurn.queries_executed
        - Enables "show me previous query" feature
    """
    # TODO: Extract from query and execution contexts
    # Build list of query dicts
    raise NotImplementedError("Extract queries")


def calculate_tokens(state: BIAgentState, task_result: dict) -> int:
    """
    Calculate tokens used in this TODO execution.

    Args:
        state: Current state
        task_result: ToolResult from execution

    Returns:
        Total tokens used (input + output)

    Implementation Notes:
        - Check task_result.metadata for token counts
        - LLM tools report tokens, traditional tools don't
        - Aggregate all LLM calls in this TODO
        - Used for cost tracking and monitoring
    """
    # TODO: Extract from task_result.metadata
    # Sum up all token counts
    return 0  # Placeholder


def extract_entities_from_message(message: str) -> list[str]:
    """
    Extract entity mentions from message text.

    Simple extraction for last TODO context detection.

    Args:
        message: Message text

    Returns:
        List of potential entity names

    Implementation Notes:
        - Simple keyword extraction (capital words, etc.)
        - Not full NER, just for context
        - Used to detect if user referenced same entities
    """
    # TODO: Simple extraction (capital words, quoted strings)
    raise NotImplementedError("Extract entities from message")
