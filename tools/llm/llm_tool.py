"""LLM tool for completions and structured outputs."""

from typing import Type, Any
from pydantic import BaseModel
from tools.base import BaseTool, ToolResult
from services.llm_service import LLMService


class LLMTool(BaseTool):
    """
    Stateless LLM completion tool.
    Wraps LLMService for use in nodes.
    """

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    @property
    def name(self) -> str:
        return "llm"

    @property
    def description(self) -> str:
        return "Execute LLM completion with optional structured output"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "User prompt"},
                "system": {"type": "string", "description": "System prompt (optional)"},
                "response_format": {
                    "type": "string",
                    "enum": ["text", "json"],
                    "default": "text",
                    "description": "Response format"
                },
                "template_name": {
                    "type": "string",
                    "description": "Name of prompt template from prompts.yaml (optional)"
                },
            },
            "required": ["prompt"]
        }

    def execute(
        self,
        prompt: str,
        system: str | None = None,
        response_format: str = "text",
        template_name: str | None = None,
        **kwargs
    ) -> ToolResult:
        """
        Execute LLM completion.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            response_format: "text" or "json"
            template_name: Name of template to use from prompts.yaml
            **kwargs: Additional template variables
        """
        try:
            # Use template if specified
            if template_name:
                template = self.llm_service.get_prompt_template(template_name)
                system = template.get("system", system)
                user_template = template.get("user_template", prompt)
                prompt = user_template.format(**kwargs) if kwargs else user_template

            # Execute completion
            if response_format == "json":
                # For JSON, use structured output with a generic schema
                class GenericJSON(BaseModel):
                    data: dict

                result = self.llm_service.structured_output(
                    prompt=prompt,
                    schema=GenericJSON,
                    system=system,
                )
                data = result.data
            else:
                data = self.llm_service.complete(prompt=prompt, system=system)

            return ToolResult(
                success=True,
                data=data,
                metadata={"response_format": response_format}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
