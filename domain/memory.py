"""Memory interfaces and implementations.

Manages conversation history across different time horizons:
- ShortTermMemory: Last N turns in memory (fast, injected into prompts)
- LongTermMemory: All turns in vector DB (persistent, semantic search)
"""

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from services.embedding_service import EmbeddingService
    from services.vectordb_service import VectorDBService

from domain.conversation import ConversationTurn


class MemoryProtocol(Protocol):
    """
    Interface for memory implementations.

    Any memory implementation must support these core operations.
    """

    def add_turn(self, turn: ConversationTurn) -> None:
        """
        Add completed turn to memory.

        Args:
            turn: Completed conversation turn

        Implementation Notes:
            - Should handle storage limits (eviction, etc.)
            - Should be idempotent (safe to call multiple times)
        """
        ...

    def get_recent_context(self, n: int = 1) -> str:
        """
        Get last N turns as context string.

        Args:
            n: Number of recent turns to include

        Returns:
            Formatted context string for prompt injection

        Implementation Notes:
            - Format should be concise for token efficiency
            - Should handle n > available turns gracefully
        """
        ...

    def clear(self) -> None:
        """
        Clear memory.

        Implementation Notes:
            - Should be safe to call even if empty
            - Should reset any internal counters
        """
        ...


class ShortTermMemory:
    """
    Keeps last N conversation turns in memory.

    This is what gets injected into prompts as context for classify_intent
    and other nodes that need recent conversation history.

    Memory Lifecycle:
        1. Initialized with max_turns limit (default: 3)
        2. After each TODO completion, add_turn() called with ConversationTurn
        3. If over limit, oldest turn evicted (FIFO)
        4. get_recent_context() formats turns for prompt injection

    Attributes:
        max_turns: Maximum number of turns to keep
        turns: List of recent conversation turns (newest last)

    Implementation Notes:
        - In-memory only, not persisted
        - FIFO eviction when over limit
        - Used by MemoryManager to build context for prompts
    """

    def __init__(self, max_turns: int = 3):
        """
        Initialize short-term memory.

        Args:
            max_turns: Maximum turns to keep (default: 3)
                Typical values: 1-5 (too many = expensive prompts)

        Implementation Notes:
            - max_turns should balance context vs token cost
            - 3 is a good default for most use cases
        """
        self.max_turns = max_turns
        self.turns: list[ConversationTurn] = []

    def add_turn(self, turn: ConversationTurn) -> None:
        """
        Add turn, evict oldest if over limit.

        Args:
            turn: Completed conversation turn to add

        Implementation Notes:
            - Append to end (newest last)
            - If len > max_turns, pop from beginning (oldest first)
            - FIFO eviction policy
        """
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)  # Remove oldest

    def get_recent_context(self, n: int = 1) -> str:
        """
        Get last N turns formatted for prompt context.

        Args:
            n: Number of recent turns to include (default: 1)
                If n > available turns, returns all available

        Returns:
            Formatted context string with user/assistant exchanges
            Example output:
                User: Show shipments to Miami
                Assistant: Which Miami? Port of Miami or Miami Container Terminal?

                User: Port of Miami
                Assistant: Found 42 shipments...

        Implementation Notes:
            - Use turn.to_context_string() for each turn
            - Join with double newline for readability
            - If no turns available, return empty string
            - Handle n > len(turns) gracefully
        """
        recent = self.turns[-n:] if n <= len(self.turns) else self.turns
        return "\n\n".join(turn.to_context_string() for turn in recent)

    def get_last_turn(self) -> ConversationTurn | None:
        """
        Get most recent turn.

        Returns:
            Last turn or None if empty

        Implementation Notes:
            - Used by classify_intent to check last TODO context
            - Returns None if turns list is empty
        """
        return self.turns[-1] if self.turns else None

    def get_all_turns(self) -> list[ConversationTurn]:
        """
        Get all turns in memory.

        Returns:
            List of all conversation turns (oldest first)

        Implementation Notes:
            - Returns copy to prevent external modification
            - Used for debugging or full context retrieval
        """
        return list(self.turns)

    def clear(self) -> None:
        """
        Clear all turns.

        Used when user explicitly clears conversation or starts fresh.

        Implementation Notes:
            - Resets turns list to empty
            - Does NOT affect long-term memory (vector DB)
        """
        self.turns.clear()


class LongTermMemory:
    """
    Persists all conversation turns to vector DB.

    Enables semantic search over conversation history for future features
    like "show me queries about vessels" or "find similar requests".

    Memory Lifecycle:
        1. After each TODO completion, persist_turn() called
        2. Turn embedded via to_embedding_text()
        3. Stored in vector DB with metadata
        4. Later: search() retrieves relevant past turns

    Attributes:
        vectordb_service: Vector DB interface (ChromaDB, Redis, etc.)
        embedding_service: Embedding generation service
        collection_name: Vector DB collection for conversation history

    Implementation Notes:
        - Currently write-only (search not implemented yet)
        - Embeds full turn context (question, intent, entities, queries, results)
        - Metadata stored for filtering (turn_id, timestamp, intent)
    """

    def __init__(
        self,
        vectordb_service: "VectorDBService",
        embedding_service: "EmbeddingService",
        collection_name: str = "conversation_history"
    ):
        """
        Initialize long-term memory.

        Args:
            vectordb_service: Vector DB implementation
            embedding_service: Embedding generation service
            collection_name: Collection name in vector DB (default: "conversation_history")

        Implementation Notes:
            - Collection created if doesn't exist
            - Should handle vector DB connection errors gracefully
        """
        self.vectordb_service = vectordb_service
        self.embedding_service = embedding_service
        self.collection_name = collection_name

    def persist_turn(self, turn: ConversationTurn) -> None:
        """
        Persist a conversation turn to vector DB.

        Embeds the turn using to_embedding_text() and stores with metadata.

        Args:
            turn: Completed conversation turn to persist

        Raises:
            VectorDBError: If storage fails

        Implementation Flow:
            1. Generate embedding text via turn.to_embedding_text()
                - Includes: question, intent, entities, queries, results
            2. Get embedding vector from embedding_service
            3. Prepare metadata dict (turn_id, timestamp, intent, etc.)
            4. Upsert to vector DB with vector + metadata + text

        Implementation Notes:
            - Should be idempotent (same turn_id overwrites)
            - Errors should be logged but not fail the turn
            - Metadata should be searchable/filterable
        """
        # TODO: Generate embedding text
        # text = turn.to_embedding_text()

        # TODO: Get embedding vector
        # embedding = self.embedding_service.embed_text(text)

        # TODO: Prepare metadata
        # metadata = {
        #     "turn_id": turn.turn_id,
        #     "timestamp": turn.started_at.isoformat(),
        #     "intent": turn.intent_detected,
        #     "rewritten_question": turn.rewritten_question or "",
        #     "entities": str(turn.entities_extracted),
        #     "queries_executed": str(turn.queries_executed),
        #     "query_metadata": str(turn.query_metadata),
        # }

        # TODO: Store in vector DB
        # self.vectordb_service.upsert(
        #     collection=self.collection_name,
        #     vectors=[embedding],
        #     metadata=[metadata],
        #     texts=[text]
        # )

        raise NotImplementedError("Implement vector DB persistence")

    def search(
        self,
        query_text: str,
        limit: int = 5,
        filter_dict: dict | None = None
    ) -> list[dict]:
        """
        Semantic search over conversation history.

        Args:
            query_text: Natural language search query
                Example: "show me queries about vessels"
            limit: Maximum results to return (default: 5)
            filter_dict: Optional metadata filters
                Example: {"intent": "data_retrieval"}

        Returns:
            List of matching turns with scores
            Example: [
                {
                    "turn_id": 5,
                    "text": "Question: Show shipments...",
                    "metadata": {...},
                    "score": 0.89
                },
                ...
            ]

        Raises:
            VectorDBError: If search fails

        Implementation Flow:
            1. Generate embedding for query_text
            2. Search vector DB with embedding + filters
            3. Return results with scores

        Implementation Notes:
            - Not implemented yet (reserved for future)
            - Will enable "find similar requests" feature
            - Should handle empty results gracefully
        """
        # TODO: Get query embedding
        # query_embedding = self.embedding_service.embed_text(query_text)

        # TODO: Search vector DB
        # results = self.vectordb_service.search(
        #     collection=self.collection_name,
        #     query_vector=query_embedding,
        #     limit=limit,
        #     filter_dict=filter_dict
        # )

        # return results

        raise NotImplementedError("Semantic search not implemented yet")

    def get_turn_by_id(self, turn_id: int) -> ConversationTurn | None:
        """
        Retrieve specific turn by ID.

        Args:
            turn_id: Turn ID to retrieve

        Returns:
            ConversationTurn if found, None otherwise

        Implementation Notes:
            - Future feature for debugging or replay
            - Requires storing full turn in metadata
        """
        raise NotImplementedError("Turn retrieval not implemented yet")

    def clear(self) -> None:
        """
        Clear all conversation history from vector DB.

        WARNING: This is destructive and cannot be undone.

        Raises:
            VectorDBError: If deletion fails

        Implementation Notes:
            - Should drop entire collection
            - Should recreate empty collection
            - Use with caution in production
        """
        raise NotImplementedError("Clear not implemented yet")
