"""MCP server setup (future implementation)."""

from tools.registry import ToolRegistry


def create_mcp_server(registry: ToolRegistry):
    """
    Create MCP server exposing all registered tools.

    Args:
        registry: Tool registry with tools to expose

    Returns:
        MCP server instance
    """
    # TODO: Implement MCP server
    # tool_definitions = registry.get_mcp_definitions()
    # mcp_server = MCPServer(tools=tool_definitions)
    # return mcp_server

    raise NotImplementedError("MCP server not yet implemented")
