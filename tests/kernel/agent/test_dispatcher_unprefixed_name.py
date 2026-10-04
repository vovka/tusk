import types

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.confirmation.confirmation_gate import ConfirmationGate
from tusk.kernel.agent.orchestrator_tool_dispatcher import OrchestratorToolDispatcher
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult


def _dispatcher(names: tuple[str, ...], seen: list[str]) -> OrchestratorToolDispatcher:
    registry = ToolRegistry()
    for name in names:
        registry.register(make_registry_tool(name, "ok", execute=lambda arguments, name=name: seen.append(name) or ToolResult(True, "ok")))
    return OrchestratorToolDispatcher(registry, types.SimpleNamespace(), types.SimpleNamespace(), confirmation=ConfirmationGate(registry))


def test_unprefixed_name_runs_the_unique_matching_tool() -> None:
    seen: list[str] = []
    call = ToolCall("switch_workspace", {"text": "2"})
    assert _dispatcher(("gnome.switch_workspace",), seen).dispatch(call, lambda tool_call: None).success is True
    assert seen == ["gnome.switch_workspace"]


def test_ambiguous_unprefixed_name_stays_unknown() -> None:
    seen: list[str] = []
    call = ToolCall("stop", {"text": "x"})
    result = _dispatcher(("coding.stop", "dictation.stop"), seen).dispatch(call, lambda tool_call: None)
    assert result.message == "unknown tool: stop" and seen == []
