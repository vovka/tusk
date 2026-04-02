from collections.abc import Callable

from tusk.shared.schemas.tool_call import ToolCall
from tusk.shared.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry
from tusk.kernel.agent.agent_tool_catalog import AgentToolCatalog

__all__ = ["OrchestratorToolDispatcher"]


class OrchestratorToolDispatcher:
    def __init__(self, tool_registry: ToolRegistry, catalog: AgentToolCatalog) -> None:
        self._registry = tool_registry
        self._catalog = catalog

    def dispatch(
        self, tool_call: ToolCall, run_agent: Callable[[ToolCall], ToolResult],
    ) -> ToolResult:
        if tool_call.tool_name == "run_agent":
            return run_agent(tool_call)
        if tool_call.tool_name == "list_available_tools":
            return self._catalog.list_tools()
        return self._real_tool(tool_call)

    def _real_tool(self, tool_call: ToolCall) -> ToolResult:
        try:
            return self._registry.get(tool_call.tool_name).execute(tool_call.parameters)
        except KeyError:
            return ToolResult(False, f"unknown tool: {tool_call.tool_name}")
