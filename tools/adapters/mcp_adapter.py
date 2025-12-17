"""MCP tool execution adapter (future implementation)."""

from tools.base import BaseTool, ToolResult


class MCPToolAdapter:
    """Run tools via MCP protocol (future implementation)."""

    def __init__(self, mcp_client=None):
        self.client = mcp_client

    def execute(self, tool: BaseTool, **kwargs) -> ToolResult:
        """
        Call tool via MCP.
        Tool signature must match MCP schema.
        """
        # TODO: Implement MCP call
        # result = await self.client.call_tool(tool.name, **kwargs)
        # return ToolResult(success=True, data=result)
        raise NotImplementedError("MCP adapter not yet implemented")
