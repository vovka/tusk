import types

from tusk.kernel.coding_router import CodingRouter
from tusk.shared.schemas.edit_operation import EditOperation
from tusk.shared.schemas.tool_result import ToolResult


def test_process_applies_each_operation_via_strategy() -> None:
    applied: list[EditOperation] = []
    router = CodingRouter(_registry([], True), types.SimpleNamespace(), object(), _strategy(applied), _log())
    result = router.process(_state(), "rename the function")
    assert result.handled is True
    assert applied == [EditOperation("replace", 1, 1, "def renamed():", "def renamed():")]


def test_process_replies_silently_on_success() -> None:
    router = CodingRouter(_registry([], True), types.SimpleNamespace(), object(), _strategy([]), _log())
    result = router.process(_state(), "rename the function")
    assert result.reply == ""


def test_process_reports_failure_when_apply_raises() -> None:
    def boom(edit: object, driver: object) -> None:
        raise RuntimeError("xdotool missing")

    strategy = types.SimpleNamespace(apply=boom)
    router = CodingRouter(_registry([], True), types.SimpleNamespace(), object(), strategy, _log())
    result = router.process(_state(), "rename the function")
    assert result.handled is False
    assert "couldn't apply" in result.reply.lower()


def test_process_reports_failure_when_adapter_errors() -> None:
    router = CodingRouter(_registry([], False), types.SimpleNamespace(), object(), _strategy([]), _log())
    result = router.process(_state(), "do thing")
    assert result.handled is False
    assert result.reply == "planning failed"


def test_process_reports_failure_on_malformed_operation() -> None:
    malformed = ToolResult(True, "ok", {"operations": [{"unexpected": 1}]})
    registry = types.SimpleNamespace(get=lambda name: _tool([], name, malformed))
    router = CodingRouter(registry, types.SimpleNamespace(), object(), _strategy([]), _log())
    result = router.process(_state(), "rename the function")
    assert result.handled is False
    assert "couldn't apply" in result.reply.lower()


def test_process_reports_failure_when_data_is_not_a_dict() -> None:
    malformed = ToolResult(True, "ok", ["operations"])
    registry = types.SimpleNamespace(get=lambda name: _tool([], name, malformed))
    router = CodingRouter(registry, types.SimpleNamespace(), object(), _strategy([]), _log())
    result = router.process(_state(), "rename the function")
    assert result.handled is False
    assert "couldn't apply" in result.reply.lower()


def test_stop_calls_adapter_and_controller() -> None:
    calls: list[tuple[str, dict]] = []
    controller = types.SimpleNamespace(stop_coding=lambda: calls.append(("controller.stop_coding", {})))
    router = CodingRouter(_registry(calls, True), controller, object(), _strategy([]), _log())
    result = router.stop(_state())
    assert result.handled is True
    assert calls == [("coding.stop_coding_session", {"session_id": "s1"}), ("controller.stop_coding", {})]


def _registry(calls: list, success: bool) -> object:
    def get(name: str) -> object:
        if name == "coding.process_intent":
            return _tool(calls, name, ToolResult(success, "ok" if success else "planning failed", _ops() if success else None))
        return _tool(calls, name, ToolResult(True, "stopped"))

    return types.SimpleNamespace(get=get)


def _tool(calls: list, name: str, result: ToolResult) -> object:
    return types.SimpleNamespace(execute=lambda args: calls.append((name, args)) or result)


def _ops() -> dict:
    return {"operations": [{"kind": "replace", "target_start": 1, "target_end": 1, "new_text": "def renamed():", "full_buffer": "def renamed():"}]}


def _strategy(applied: list) -> object:
    return types.SimpleNamespace(apply=lambda edit, driver: applied.append(edit))


def _state() -> object:
    return types.SimpleNamespace(adapter_name="coding", session_id="s1")


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
