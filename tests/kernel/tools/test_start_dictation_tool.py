import types

from tusk.kernel.modes.mode_state import ModeState
from tusk.kernel.tools.start_dictation_tool import StartDictationTool
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.tools.tool_result import ToolResult


def test_execute_starts_session_and_mode_slot() -> None:
    states: list[ModeState] = []
    result = StartDictationTool(_registry(), _slot(states), _manager()).execute({})
    assert result.success is True
    assert states == [ModeState("dictation", "sid", "gnome")]


def test_execute_reports_when_adapter_missing() -> None:
    result = StartDictationTool(_missing_registry(), _slot([]), _manager()).execute({})
    assert result == ToolResult(False, "dictation adapter is not available")


def _registry() -> object:
    tool = types.SimpleNamespace(execute=lambda args: ToolResult(True, "started", {"session_id": "sid"}))
    return types.SimpleNamespace(get=lambda name: tool)


def _missing_registry() -> object:
    def get(name: str) -> object:
        raise KeyError(name)

    return types.SimpleNamespace(get=get)


def _slot(states: list) -> object:
    return types.SimpleNamespace(start=lambda state: states.append(state) or KernelResponse(True, "Dictation started."))


def _manager() -> object:
    return types.SimpleNamespace(primary_desktop_source=lambda: "gnome")
