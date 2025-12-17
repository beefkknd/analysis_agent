"""Tool registry for local and MCP execution.

Central registry manages all tools with unified interface for:
- Local execution (current)
- MCP execution (future)
- Tool discovery and introspection
"""

from typing import Dict
from tools.base import BaseTool, ToolResult
from tools.adapters.local_adapter import LocalToolAdapter


class ToolRegistry:
    """
    Central registry for all tools.

    Handles both local execution and MCP exposure with unified interface.
    Nodes call registry.execute() without knowing execution mode.

    Architecture:
        ┌─────────────────────────────────────┐
        │          Nodes                      │
        │  registry.execute("tool", ...)      │
        └────────────────┬────────────────────┘
                         │
        ┌────────────────▼────────────────────┐
        │        ToolRegistry                 │
        │   - Tool storage (_tools dict)      │
        │   - Mode selection (local vs MCP)   │
        └────────────────┬────────────────────┘
                         │
         ┌───────────────┴────────────────┐
         │                                │
    ┌────▼────┐                    ┌─────▼──────┐
    │  Local  │                    │    MCP     │
    │ Adapter │                    │  Adapter   │
    │ (current)│                    │  (future)  │
    └─────────┘                    └────────────┘

    Attributes:
        mode: Execution mode ("local" or "mcp")
        _tools: Dict mapping tool names to tool instances
        _adapter: Execution adapter (LocalToolAdapter or MCPAdapter)

    Example Usage:
        # Setup
        registry = ToolRegistry(mode="local")
        registry.register(EntityResolutionTool())
        registry.register(ESExecutorTool())

        # Execute tool (from node)
        result = registry.execute(
            "entity_resolution",
            entities={"vessel": ["Anna"]},
            context="Show shipments..."
        )

        # Check result
        if result.success:
            data = result.data
        else:
            error = result.error

    Implementation Notes:
        - All nodes use registry.execute() for tool calls
        - Mode can be swapped without changing node code
        - Tools registered once at agent init, reused per turn
    """

    def __init__(self, mode: str = "local"):
        """
        Initialize registry.

        Args:
            mode: Execution mode
                - "local": Run tools directly in process (current)
                - "mcp": Run tools via MCP protocol (future)

        Raises:
            ValueError: If mode not supported

        Implementation Notes:
            - "local" mode uses LocalToolAdapter
            - "mcp" mode not implemented yet
            - Default to "local" for now
        """
        self.mode = mode
        self._tools: Dict[str, BaseTool] = {}
        self._adapter = self._create_adapter(mode)

    def _create_adapter(self, mode: str):
        """
        Factory for tool execution adapter.

        Args:
            mode: Execution mode ("local" or "mcp")

        Returns:
            Tool adapter instance

        Raises:
            ValueError: If mode not supported

        Implementation Notes:
            - LocalToolAdapter: Calls tool.execute() directly
            - MCPAdapter (future): Serializes inputs, calls MCP server, deserializes response
        """
        if mode == "local":
            return LocalToolAdapter()
        elif mode == "mcp":
            # TODO: Implement MCP adapter
            # from tools.adapters.mcp_adapter import MCPAdapter
            # return MCPAdapter(server_url=..., auth_token=...)
            raise NotImplementedError("MCP adapter not yet implemented")
        else:
            raise ValueError(f"Unknown mode: {mode}. Must be 'local' or 'mcp'")

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool for use.

        Args:
            tool: Tool instance implementing BaseTool interface

        Raises:
            ValueError: If tool with same name already registered

        Implementation Notes:
            - Tools registered by name (tool.name)
            - Duplicate names rejected (prevents shadowing)
            - Called during agent initialization
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.

        Args:
            tool_name: Name of tool to remove

        Implementation Notes:
            - Used for testing or dynamic tool management
            - Safe to call if tool doesn't exist (no-op)
        """
        self._tools.pop(tool_name, None)

    def get(self, name: str) -> BaseTool:
        """
        Get tool instance (for direct use in nodes).

        Args:
            name: Tool name

        Returns:
            Tool instance

        Raises:
            KeyError: If tool not found

        Implementation Notes:
            - Use for direct tool access (rare)
            - Prefer execute() for normal tool calls
            - Useful for introspection (checking can_clarify, etc.)
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def has_tool(self, name: str) -> bool:
        """
        Check if tool registered.

        Args:
            name: Tool name to check

        Returns:
            True if tool exists, False otherwise

        Implementation Notes:
            - Used for conditional tool execution
            - Safe alternative to get() when existence uncertain
        """
        return name in self._tools

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute tool through adapter.

        Works same whether local or MCP - nodes don't need to know.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool-specific parameters matching input_schema

        Returns:
            ToolResult with success, data, error, metadata

        Example:
            result = registry.execute(
                "entity_resolution",
                entities={"vessel": ["Anna"]},
                context="Show shipments from Anna"
            )

            if result.success:
                if result.clarification:
                    # Ask user clarification
                    question = result.clarification["question"]
                else:
                    # Process result
                    data = result.data
            else:
                # Handle error
                print(result.error)

        Implementation Notes:
            - Returns error ToolResult if tool not found (doesn't raise)
            - Adapter handles actual execution (local vs MCP)
            - Clarification handled via result.clarification field
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool {tool_name} not found in registry"
            )

        # Execute through adapter (local or MCP)
        return self._adapter.execute(tool, **kwargs)

    def list_tools(self) -> list[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names

        Example:
            ["llm_tool", "entity_resolution", "es_executor", ...]

        Implementation Notes:
            - Used for introspection and debugging
            - Useful for MCP tool discovery
        """
        return list(self._tools.keys())

    def get_tools_by_capability(self, can_clarify: bool | None = None) -> list[str]:
        """
        Get tools filtered by capability.

        Args:
            can_clarify: Filter by clarification capability
                - True: Only LLM-enabled tools
                - False: Only traditional tools
                - None: All tools

        Returns:
            List of matching tool names

        Example:
            # Get all LLM-enabled tools
            llm_tools = registry.get_tools_by_capability(can_clarify=True)
            # ["entity_resolution", "field_mapping", "query_builder"]

        Implementation Notes:
            - Used by plan_todos to determine which tools support clarification
            - Helps with tool selection logic
        """
        if can_clarify is None:
            return self.list_tools()

        return [
            name for name, tool in self._tools.items()
            if tool.can_clarify == can_clarify
        ]

    def get_mcp_definitions(self) -> list[dict]:
        """
        Generate MCP tool definitions for all tools.

        Used by MCP server to expose tools to external clients.

        Returns:
            List of MCP tool definition dicts

        Example:
            [
                {
                    "name": "entity_resolution",
                    "description": "Resolves entity mentions...",
                    "inputSchema": {
                        "type": "object",
                        "properties": {...}
                    }
                },
                ...
            ]

        Implementation Notes:
            - Called by MCP server during initialization
            - Each tool's to_mcp_definition() method used
            - Format compatible with MCP protocol spec
        """
        return [
            tool.to_mcp_definition()
            for tool in self._tools.values()
        ]

    def get_tool_info(self, tool_name: str) -> dict:
        """
        Get detailed info about a tool.

        Args:
            tool_name: Name of tool

        Returns:
            Dict with tool metadata

        Example:
            {
                "name": "entity_resolution",
                "description": "Resolves entity mentions...",
                "can_clarify": True,
                "brutal_force": False,
                "input_schema": {...}
            }

        Raises:
            KeyError: If tool not found

        Implementation Notes:
            - Used for debugging and introspection
            - Provides complete tool interface info
        """
        tool = self.get(tool_name)
        return {
            "name": tool.name,
            "description": tool.description,
            "can_clarify": tool.can_clarify,
            "brutal_force": tool.brutal_force,
            "input_schema": tool.input_schema()
        }

    def validate_tool_call(self, tool_name: str, **kwargs) -> tuple[bool, str | None]:
        """
        Validate tool call before execution.

        Args:
            tool_name: Name of tool to validate
            **kwargs: Tool parameters to validate

        Returns:
            (valid, error_message) tuple

        Example:
            valid, error = registry.validate_tool_call(
                "entity_resolution",
                entities={"vessel": ["Anna"]}
            )
            if not valid:
                print(f"Validation error: {error}")

        Implementation Notes:
            - Checks tool exists
            - Validates parameters against input_schema
            - Returns error message if invalid
            - Can be called before execute() to fail fast
        """
        if tool_name not in self._tools:
            return (False, f"Tool '{tool_name}' not found")

        tool = self._tools[tool_name]
        return tool.validate_inputs(**kwargs)

    def clear(self) -> None:
        """
        Clear all registered tools.

        Implementation Notes:
            - Used for testing or fresh start
            - Agent init will re-register tools
        """
        self._tools.clear()

    def __repr__(self) -> str:
        """String representation for debugging."""
        tools_str = ", ".join(self.list_tools())
        return f"ToolRegistry(mode={self.mode}, tools=[{tools_str}])"
