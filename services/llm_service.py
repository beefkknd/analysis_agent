"""LLM service abstraction using LangChain."""

from typing import Type, Any
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
import yaml

from config.settings import Settings


class LLMService:
    """
    LLM operations abstraction using LangChain.

    Supports multiple providers (OpenAI, Anthropic) and handles:
    - Standard completions
    - Structured outputs with Pydantic schemas
    - Prompt template management
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = self._init_llm()
        self.prompts = self._load_prompts()

    def _init_llm(self):
        """Initialize LLM client based on settings."""
        if self.settings.llm_provider == "openai":
            return ChatOpenAI(
                model=self.settings.llm_model,
                api_key=self.settings.openai_api_key,
                temperature=0.0,
            )
        elif self.settings.llm_provider == "anthropic":
            return ChatAnthropic(
                model=self.settings.llm_model,
                api_key=self.settings.anthropic_api_key,
                temperature=0.0,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")

    def _load_prompts(self) -> dict:
        """Load prompt templates from YAML file."""
        with open(self.settings.prompts_file, 'r') as f:
            return yaml.safe_load(f)

    def complete(self, prompt: str, system: str | None = None, **kwargs) -> str:
        """
        Standard completion.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            **kwargs: Additional parameters for LLM

        Returns:
            Completion text
        """
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        response = self.llm.invoke(messages, **kwargs)
        return response.content

    def structured_output(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system: str | None = None,
    ) -> BaseModel:
        """
        Structured output with Pydantic schema.

        Args:
            prompt: User prompt
            schema: Pydantic model class for output structure
            system: System prompt (optional)

        Returns:
            Instance of schema populated with LLM output
        """
        structured_llm = self.llm.with_structured_output(schema)

        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        return structured_llm.invoke(messages)

    def get_prompt_template(self, template_name: str) -> dict:
        """
        Get prompt template by name.

        Args:
            template_name: Name of template from prompts.yaml

        Returns:
            Dictionary with 'system' and 'user_template' keys
        """
        if template_name not in self.prompts:
            raise ValueError(f"Prompt template '{template_name}' not found")
        return self.prompts[template_name]
