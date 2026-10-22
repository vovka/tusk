from dataclasses import replace

from tusk.kernel.agent.confirmation.confirmation_gate import ConfirmationGate
from tusk.kernel.agent.tool_sequence.executor import Executor
from tusk.kernel.agent.toolset.simple_schema_validator import SimpleSchemaValidator
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.interfaces.tracer import Tracer
from tusk.shared.observability.null_tracer import NullTracer
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.shared.schemas.tools.tool_sequence_plan import ToolSequencePlan

__all__ = ["OrchestratorToolDispatcher"]


class OrchestratorToolDispatcher:
    def __init__(self, tool_registry: ToolRegistry, sequence_executor: Executor, validator: SimpleSchemaValidator | None = None, tracer: Tracer | None = None, *, confirmation: ConfirmationGate) -> None:
        self._registry = tool_registry
        self._sequence = sequence_executor
        self._validator = validator or SimpleSchemaValidator()
        self._tracer = tracer or NullTracer()
        self._confirmation = confirmation

    def dispatch(
        self,
        tool_call: ToolCall,
        session_id: str = "",
        allowed_tool_names: set[str] | None = None,
        sequence_plan: ToolSequencePlan | None = None,
    ) -> ToolResult:
        if tool_call.tool_name == "execute_tool_sequence":
            return self._execute_sequence(session_id, allowed_tool_names, sequence_plan)
        return self._real_tool(self._with_full_name(tool_call))

    def _execute_sequence(
        self,
        session_id: str,
        allowed_tool_names: set[str] | None,
        sequence_plan: ToolSequencePlan | None,
    ) -> ToolResult:
        return self._sequence.execute_plan(session_id, sequence_plan, allowed_tool_names or set())

    def _with_full_name(self, tool_call: ToolCall) -> ToolCall:
        return replace(tool_call, tool_name=self._registry.resolve_name(tool_call.tool_name))

    def _real_tool(self, tool_call: ToolCall) -> ToolResult:
        try:
            tool = self._registry.get(tool_call.tool_name)
        except KeyError:
            return ToolResult(False, f"unknown tool: {tool_call.tool_name}")
        error = self._validator.validate(tool.input_schema, tool_call.parameters)
        if error is not None:
            return ToolResult(False, f"invalid arguments for {tool_call.tool_name}: {error}")
        return self._traced_execute(tool, tool_call)

    def _traced_execute(self, tool: object, tool_call: ToolCall) -> ToolResult:
        with self._tracer.span(f"tool.{tool_call.tool_name}", {"tool": tool_call.tool_name}) as span:
            result = self._confirmation.execute(tool_call.tool_name, tool_call.parameters)
            span.set_attribute("success", str(result.success))
        return result
