"""Settings management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses .env file for local development.
    """

    # LLM Configuration
    llm_provider: Literal["openai", "anthropic"] = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Embedding Configuration
    embedding_provider: Literal["openai", "local"] = "openai"
    embedding_model: str = "text-embedding-3-small"

    # Vector Database Configuration
    vector_db_type: Literal["chroma", "redis"] = "chroma"
    chroma_persist_dir: str = "./data/chroma"
    redis_url: str = "redis://localhost:6379"

    # Elasticsearch Configuration
    es_url: str = "http://localhost:9200"
    es_index: str = "business_data"

    # GraphQL Configuration
    graphql_endpoint: str = "http://localhost:4000/graphql"

    # Agent Configuration
    prompts_file: str = "config/prompts.yaml"
    short_term_memory_turns: int = 3
    max_iterations: int = 10
    yolo_mode: bool = False  # Auto-execute queries without asking for permission (like --trust flag)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def llm_api_key(self) -> str:
        """Get the appropriate API key based on provider."""
        if self.llm_provider == "openai":
            return self.openai_api_key
        elif self.llm_provider == "anthropic":
            return self.anthropic_api_key
        return ""
