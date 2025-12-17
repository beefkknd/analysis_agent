"""LangGraph checkpointer configuration."""

from langgraph.checkpoint.memory import MemorySaver
from config.settings import Settings


def create_checkpointer(settings: Settings):
    """
    Create checkpointer for LangGraph.

    Uses in-memory checkpointer for now.
    Future: Can use SqliteSaver or PostgresSaver for persistence.

    Args:
        settings: Application settings

    Returns:
        Checkpointer instance
    """
    # For now, use in-memory checkpointer
    return MemorySaver()

    # Future: Use persistent checkpointer
    # from langgraph.checkpoint.sqlite import SqliteSaver
    # return SqliteSaver.from_conn_string(settings.checkpoint_db_path)
