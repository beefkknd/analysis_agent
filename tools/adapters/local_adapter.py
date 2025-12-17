"""Local tool execution adapter."""

from tools.base import BaseTool, ToolResult


class LocalToolAdapter:
    """Run tools directly in-process (current mode)."""

    def execute(self, tool: BaseTool, **kwargs) -> ToolResult:
        """Execute tool directly."""
        return tool.execute(**kwargs)
