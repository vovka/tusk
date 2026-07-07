import types

from tusk.kernel.modes.coding_state import CodingState
from tusk.kernel.tools.start_coding_tool import StartCodingTool
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.tool_result import ToolResult


def test_execute_reads_buffer_and_starts_session() -> None:
    states: list[CodingState] = []
    tool = StartCodingTool(_registry(True), _controller(states), _manager(), _driver())
    result = tool.execute({})
    assert result.success is True
    assert states == [CodingState("coding", "sid", "gnome")]


def test_execute_seeds_session_with_buffer_contents() -> None:
    calls: list[dict] = []
    tool = StartCodingTool(_registry(True, calls), _controller([]), _manager(), _driver())
    tool.execute({})
    assert calls == [{"initial_buffer": "print(1)"}]


def test_execute_reports_when_adapter_missing() -> None:
    tool = StartCodingTool(_missing_registry(), _controller([]), _manager(), _driver())
    result = tool.execute({})
    assert result == ToolResult(False, "coding adapter is not available")


def test_execute_is_noop_when_already_coding() -> None:
    calls: list[dict] = []
    tool = StartCodingTool(_registry(True, calls), _active_controller(), _manager(), _driver())
    result = tool.execute({})
    assert result.success is True
    assert calls == []


def _active_controller() -> object:
    return types.SimpleNamespace(coding_active=True)


def _registry(success: bool, calls: list | None = None) -> object:
    def execute(args: dict) -> ToolResult:
        if calls is not None:
            calls.append(args)
        return ToolResult(success, "started", {"session_id": "sid"})

    return types.SimpleNamespace(get=lambda name: types.SimpleNamespace(execute=execute))


def _missing_registry() -> object:
    def get(name: str) -> object:
        raise KeyError(name)

    return types.SimpleNamespace(get=get)


def _controller(states: list) -> object:
    return types.SimpleNamespace(
        coding_active=False,
        start_coding=lambda state: states.append(state) or KernelResponse(True, "Coding started."),
    )


def _manager() -> object:
    return types.SimpleNamespace(primary_desktop_source=lambda: "gnome")


def _driver() -> object:
    return types.SimpleNamespace(read_buffer=lambda: "print(1)")
