"""Base tool interface and result type.

All tools inherit from BaseTool and return ToolResult.
Tools are stateless - they don't access AgentState directly.
"""

from abc import ABC, abstractmethod
from typing import Any, Literal
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """
    Standardized tool output format.

    All tools must return this format for consistent handling by nodes.

    Fields:
        success: Whether tool execution succeeded
            True = success, False = error occurred

        data: Tool output data (structure varies by tool)
            Examples:
            - Entity resolution: EntityResolutionResult
            - Query builder: ElasticsearchQuery or GraphQLQuery
            - Query executor: QueryResult
            - LLM: str or structured dict

        error: Error message if failed
            None if success=True
            Example: "Timeout after 30000ms"

        metadata: Additional context about execution
            Example: {
                "execution_time_ms": 235.5,
                "llm_model": "gpt-4o-mini",
                "tokens_used": 1250,
                "clarification_needed": True
            }

        clarification: Clarification request (for LLM-enabled tools only)
            If tool needs user input, this contains:
            - question: Question to ask user
            - context: Context for understanding question
            - options: Suggested options (if applicable)
            Example: {
                "question": "Which Miami: Port of Miami or Miami Container Terminal?",
                "context": {...},
                "options": ["Port of Miami", "Miami Container Terminal"]
            }

    Example:
        ToolResult(
            success=True,
            data=EntityResolutionResult(...),
            metadata={"execution_time_ms": 125.3}
        )

        ToolResult(
            success=False,
            data=None,
            error="Vector DB connection failed"
        )

        ToolResult(
            success=True,
            data={"clarification_needed": True},
            metadata={"tool": "entity_resolution"},
            clarification={
                "question": "Which Miami do you mean?",
                "options": ["Port of Miami", "Miami Container Terminal"]
            }
        )

    Implementation Notes:
        - Nodes check success field to determine routing
        - If clarification present, turn ends with agent asking question
        - metadata is optional but useful for debugging/monitoring
    """
    success: bool
    data: Any
    error: str | None = None
    metadata: dict = Field(default_factory=dict)
    clarification: dict | None = None  # NEW: For LLM-enabled tools


class BaseTool(ABC):
    """
    Base interface for all tools.

    Tools are stateless functions that receive inputs and return ToolResult.
    They don't access AgentState directly - nodes handle state updates.

    Tool Categories:
        1. Core Tools: LLM, embedding, vector DB
        2. LLM-Enabled Tools: Can ask clarification (entity_resolution, field_mapping, query_builder)
        3. Traditional Tools: Direct execution (es_executor, graphql_executor)
        4. Analysis Tools: Pattern recognition, stats (future)

    Attributes:
        can_clarify: Whether tool supports clarification questions
            True = LLM-enabled tool (can ask user)
            False = Traditional tool (direct execution)

        brutal_force: Whether tool can skip clarification in YOLO mode
            True = Can execute without clarification
            False = Must ask if ambiguous

    Implementation Pattern:
        class MyTool(BaseTool):
            @property
            def name(self) -> str:
                return "my_tool"

            @property
            def description(self) -> str:
                return "Does something useful"

            @property
            def can_clarify(self) -> bool:
                return True  # If LLM-enabled

            def input_schema(self) -> dict:
                return {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"}
                    },
                    "required": ["param1"]
                }

            def execute(self, param1: str) -> ToolResult:
                # Implementation here
                return ToolResult(success=True, data=result)

    MCP Exposure:
        Tools are designed to be exposed via MCP:
        - name, description, input_schema used for MCP tool definitions
        - execute() called by MCP adapter
        - ToolResult serialized to MCP response format
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool name for registration.

        Returns:
            Unique tool identifier
            Example: "entity_resolution", "es_executor"

        Implementation Notes:
            - Must be unique across all tools
            - Used for tool registry lookups
            - Used in MCP tool definitions
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Tool description for MCP/LLM.

        Returns:
            Human-readable description of what tool does

        Example:
            "Resolves entity mentions to canonical forms using vector DB semantic search"

        Implementation Notes:
            - Used by LLM for tool selection
            - Used in MCP tool catalog
            - Should be concise but descriptive
        """
        pass

    @property
    def can_clarify(self) -> bool:
        """
        Whether tool can ask clarification questions.

        Returns:
            True if LLM-enabled tool, False if traditional

        Implementation Notes:
            - LLM-enabled tools: entity_resolution, field_mapping, query_builder
            - Traditional tools: es_executor, graphql_executor
            - If True, tool can return ToolResult with clarification field set
        """
        return False  # Default: traditional tool

    @property
    def brutal_force(self) -> bool:
        """
        Whether tool can execute without clarification in YOLO mode.

        Returns:
            True if can make best-guess, False if must clarify

        Implementation Notes:
            - Used in YOLO mode to skip clarification
            - If True: Pick first/best option when ambiguous
            - If False: Must ask even in YOLO mode
        """
        return False  # Default: require clarification

    @abstractmethod
    def input_schema(self) -> dict:
        """
        JSON schema for tool inputs (MCP compatible).

        Returns:
            JSON Schema dict describing input parameters

        Example:
            {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "object",
                        "description": "Entity mentions to resolve"
                    },
                    "context": {
                        "type": "string",
                        "description": "User question for context"
                    }
                },
                "required": ["entities"]
            }

        Implementation Notes:
            - Must be valid JSON Schema
            - Used by MCP for input validation
            - Used by LLM for parameter generation
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute tool with given inputs.

        Args:
            **kwargs: Tool-specific parameters matching input_schema

        Returns:
            ToolResult with success, data, and optional error/clarification

        Raises:
            Should NOT raise exceptions - return ToolResult with error instead

        Implementation Notes:
            - Validate inputs against input_schema
            - If LLM-enabled and ambiguous, return clarification
            - If error occurs, return ToolResult(success=False, error=...)
            - Include metadata for monitoring (execution time, tokens, etc.)
        """
        pass

    def validate_inputs(self, **kwargs) -> tuple[bool, str | None]:
        """
        Validate inputs against schema.

        Args:
            **kwargs: Tool parameters to validate

        Returns:
            (valid, error_message) tuple

        Implementation Notes:
            - Called before execute() by adapters
            - Checks required fields present
            - Validates types match schema
            - Override for custom validation logic
        """
        # TODO: Implement JSON Schema validation
        # For now, assume valid
        return (True, None)

    def to_mcp_definition(self) -> dict:
        """
        Convert tool to MCP definition format.

        Returns:
            MCP tool definition dict

        Example:
            {
                "name": "entity_resolution",
                "description": "Resolves entity mentions...",
                "inputSchema": {...}
            }

        Implementation Notes:
            - Used by ToolRegistry.get_mcp_definitions()
            - Standard format for MCP tool exposure
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema()
        }
