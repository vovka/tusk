import types

from tests.kernel_api_support import make_registry_tool
from tests.recording_tracer import RecordingTracer
from tusk.kernel.agent.confirmation.confirmation_gate import ConfirmationGate
from tusk.kernel.agent.orchestrator_tool_dispatcher import OrchestratorToolDispatcher
from tusk.kernel.agent.tool_sequence.executor import Executor
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_sequence_plan import ToolSequencePlan

_NULL_STORE = types.SimpleNamespace(append_event=lambda session_id, name, data: None)


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.press_keys", "pressed", sequence_callable=True))
    return registry


def _dispatcher(registry: ToolRegistry, tracer: RecordingTracer) -> OrchestratorToolDispatcher:
    executor = Executor(registry, _NULL_STORE, confirmation=ConfirmationGate(registry))
    return OrchestratorToolDispatcher(registry, executor, tracer=tracer, confirmation=ConfirmationGate(registry))


def test_dispatcher_wraps_real_tool_execution_in_span() -> None:
    tracer = RecordingTracer()
    dispatcher = _dispatcher(_registry(), tracer)
    dispatcher.dispatch(ToolCall("gnome.press_keys", {}, "c1"))
    assert tracer.spans[0]["name"] == "tool.gnome.press_keys"
    assert tracer.spans[0]["attributes"]["success"] == "True"


def test_sequence_executor_wraps_each_step_in_span() -> None:
    tracer = RecordingTracer()
    registry = _registry()
    executor = Executor(registry, _NULL_STORE, tracer=tracer, confirmation=ConfirmationGate(registry))
    plan = {"goal": "press", "steps": [{"id": "s1", "tool_name": "gnome.press_keys", "args": {}}]}
    executor.execute_plan("session-1", ToolSequencePlan.from_dict(plan), {"gnome.press_keys"})
    assert tracer.spans[0]["name"] == "tool.gnome.press_keys"
    assert tracer.spans[0]["attributes"]["step_id"] == "s1"
    assert tracer.spans[0]["attributes"]["success"] == "True"
