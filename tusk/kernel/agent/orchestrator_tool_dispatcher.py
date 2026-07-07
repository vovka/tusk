from collections.abc import Callable

from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.kernel.agent.agent_tool_catalog import AgentToolCatalog
from tusk.kernel.agent.simple_schema_validator import SimpleSchemaValidator
from tusk.kernel.agent.tool_sequence.executor import Executor
from tusk.shared.schemas.tools.tool_sequence_plan import ToolSequencePlan

__all__ = ["OrchestratorToolDispatcher"]


class OrchestratorToolDispatcher:
    def __init__(self, tool_registry: ToolRegistry, catalog: AgentToolCatalog, sequence_executor: Executor, validator: SimpleSchemaValidator | None = None) -> None:
        self._registry = tool_registry
        self._catalog = catalog
        self._sequence = sequence_executor
        self._validator = validator or SimpleSchemaValidator()

    def dispatch(
        self,
        tool_call: ToolCall,
        run_agent: Callable[[ToolCall], ToolResult],
        session_id: str = "",
        allowed_tool_names: set[str] | None = None,
        sequence_plan: ToolSequencePlan | None = None,
    ) -> ToolResult:
        if tool_call.tool_name == "run_agent":
            return run_agent(tool_call)
        if tool_call.tool_name == "list_available_tools":
            return self._catalog.list_tools()
        if tool_call.tool_name == "execute_tool_sequence":
            return self._execute_sequence(session_id, allowed_tool_names, sequence_plan)
        return self._real_tool(tool_call)

    def _execute_sequence(
        self,
        session_id: str,
        allowed_tool_names: set[str] | None,
        sequence_plan: ToolSequencePlan | None,
    ) -> ToolResult:
        return self._sequence.execute_plan(session_id, sequence_plan, allowed_tool_names or set())

    def _real_tool(self, tool_call: ToolCall) -> ToolResult:
        try:
            tool = self._registry.get(tool_call.tool_name)
        except KeyError:
            return ToolResult(False, f"unknown tool: {tool_call.tool_name}")
        error = self._validator.validate(tool.input_schema, tool_call.parameters)
        if error is not None:
            return ToolResult(False, f"invalid arguments for {tool_call.tool_name}: {error}")
        return tool.execute(tool_call.parameters)
