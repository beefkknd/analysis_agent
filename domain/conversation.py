"""Conversation turn and message definitions.

These models represent the units of memory that get persisted.
One ConversationTurn = one TODO execution (not one user request).
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class Message(BaseModel):
    """
    Single message in conversation.

    Used for both user messages and agent responses.

    Fields:
        role: Message sender
            - "user": User input
            - "assistant": Agent response
            - "system": System messages (prompts, context)

        content: Message text

        timestamp: When message was created

        metadata: Additional context
            Example: {"source": "cli", "turn_id": 5, "tokens": 150}

    Example:
        Message(
            role="user",
            content="Show shipments to Miami",
            timestamp=datetime.now(),
            metadata={"turn_id": 1}
        )
    """
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class ConversationTurn(BaseModel):
    """
    One complete TODO execution cycle.

    IMPORTANT: In the new architecture, 1 turn = 1 TODO completion, NOT 1 user request.
    If 5 TODOs execute in one user request, 5 ConversationTurns are saved.

    This is the unit of memory we track in both short-term and long-term memory.

    Fields:
        turn_id: Sequential turn counter (increments per TODO completion)

        user_message: User input (could be original request or clarification answer)

        agent_response: Agent's response (could be results, clarification question, or error)

        intent_detected: What intent was classified for this turn
            Example: "data_retrieval", "exact_answer", "modification"

        rewritten_question: Clean rewrite from reiterate_intention node
            Only populated for new_request intents
            Example: "Show all shipments to Port of Miami in last 7 days"

        entities_extracted: Entities extracted during this turn
            Example: {"vessel": ["MSC ANNA"], "port": ["Port of Miami"]}

        queries_executed: List of queries executed during this turn
            Each entry is a dict with:
                - type: "elasticsearch" | "graphql"
                - query: Full query structure
                - summary: Human-readable summary
            Example: [
                {
                    "type": "elasticsearch",
                    "query": {"query": {"bool": {...}}},
                    "summary": "Search shipments by vessel and port"
                }
            ]

        query_metadata: Structured metadata for future data analysis
            This is critical for "analyze X" follow-up requests
            Structure: {
                "query_type": "elasticsearch" | "graphql",
                "query_structure": {
                    "filters": ["vessel:MSC ANNA"],
                    "time_range": "last_7_days",
                    "fields": ["vessel_name", "arrival_date"]
                },
                "result_summary": "42 shipments found",
                "how_to_retrieve": {
                    "index": "shipments",
                    "query": {...}  # Full query for re-execution
                }
            }

        started_at: When turn started

        completed_at: When turn completed

        tokens_used: LLM tokens consumed in this turn

    Memory Usage:
        - Short-term: Last N turns kept in memory, formatted via to_context_string()
        - Long-term: All turns embedded via to_embedding_text() and stored in vector DB

    Example:
        ConversationTurn(
            turn_id=3,
            user_message=Message(role="user", content="Port of Miami"),
            agent_response=Message(role="assistant", content="Continuing query..."),
            intent_detected="exact_answer",
            rewritten_question=None,  # Not a new request
            entities_extracted={},  # Already extracted in previous turn
            queries_executed=[{"type": "elasticsearch", "summary": "..."}],
            query_metadata={...},
            tokens_used=1250
        )
    """
    turn_id: int
    user_message: Message
    agent_response: Message

    # What happened during this turn
    intent_detected: str
    rewritten_question: str | None = None  # From reiterate_intention node
    entities_extracted: dict = Field(default_factory=dict)
    queries_executed: list[dict] = Field(default_factory=list)
    query_metadata: dict = Field(default_factory=dict)  # For analysis forwarding

    # Metadata
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime = Field(default_factory=datetime.now)
    tokens_used: int = 0

    def to_context_string(self) -> str:
        """
        Format for short-term memory context injection.

        Used when building prompts for classify_intent and other nodes.
        Provides recent conversation history.

        Returns:
            Simple user/assistant exchange formatted as text

        Example Output:
            User: Show shipments to Miami
            Assistant: Which Miami do you mean? Port of Miami or Miami Container Terminal?

        Implementation Notes:
            - Keep it concise for prompt injection
            - Just user input + agent response
            - No metadata or timestamps (to save tokens)
        """
        return f"User: {self.user_message.content}\nAssistant: {self.agent_response.content}"

    def to_embedding_text(self) -> str:
        """
        Format for long-term memory embedding.

        Used when persisting to vector DB for semantic search.
        Includes all relevant context for future retrieval.

        Returns:
            Rich text representation with intent, entities, queries, results

        Example Output:
            Question: Show all shipments to Port of Miami in last 7 days
            Intent: data_retrieval
            Entities: vessel:MSC ANNA, port:Port of Miami
            Queries: elasticsearch: Search shipments by vessel and port
            Results: Found 42 shipments. Top results: ...

        Implementation Notes:
            - Include rewritten_question if available (cleaner than original)
            - Include intent for semantic search ("show me data retrieval queries")
            - Include query summaries for search ("find queries about vessels")
            - Include result preview (first 200 chars) for relevance
            - This text will be embedded and stored in vector DB
        """
        parts = []

        # Rewritten question (clean version)
        if self.rewritten_question:
            parts.append(f"Question: {self.rewritten_question}")
        else:
            parts.append(f"Question: {self.user_message.content}")

        # Intent
        parts.append(f"Intent: {self.intent_detected}")

        # Entities
        if self.entities_extracted:
            entity_strs = [
                f"{entity_type}:{','.join(values)}"
                for entity_type, values in self.entities_extracted.items()
            ]
            parts.append(f"Entities: {', '.join(entity_strs)}")

        # Queries executed
        if self.queries_executed:
            query_summaries = [
                f"{q.get('type', 'unknown')}: {q.get('summary', '')}"
                for q in self.queries_executed
            ]
            parts.append(f"Queries: {', '.join(query_summaries)}")

        # Results summary from agent response (first 200 chars)
        parts.append(f"Results: {self.agent_response.content[:200]}")

        return "\n".join(parts)

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for JSON serialization

        Implementation Notes:
            - Use Pydantic's model_dump() for automatic serialization
            - Handles datetime serialization
            - Preserves all fields
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationTurn":
        """
        Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            ConversationTurn instance

        Raises:
            ValidationError: If data doesn't match schema

        Implementation Notes:
            - Use Pydantic's model_validate() for automatic parsing
            - Handles datetime parsing
            - Validates all fields
        """
        return cls.model_validate(data)
