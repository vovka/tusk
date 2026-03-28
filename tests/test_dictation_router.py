import types

from tusk.kernel.dictation_router import DictationRouter
from tusk.kernel.schemas.tool_result import ToolResult


def test_dictation_router_logs_segment_and_apply() -> None:
    calls: list[tuple[str, dict]] = []
    logs: list[tuple[str, str]] = []
    router = DictationRouter(_registry(calls, True), types.SimpleNamespace(), _log(logs))
    result = router.process(_state(), "hello world")
    assert result.handled is True
    assert calls[-1] == ("gnome.type_text", {"text": "hello world"})
    assert logs == _expected_logs()


def test_dictation_router_reports_desktop_apply_failure() -> None:
    logs: list[tuple[str, str]] = []
    router = DictationRouter(_registry([], False), types.SimpleNamespace(), _log(logs))
    result = router.process(_state(), "hello world")
    assert result.handled is False
    assert result.reply == "typing failed"
    assert logs[-1] == ("DICTATION", "apply failed via gnome: typing failed")


def test_dictation_router_stops_via_adapter_stop_tool() -> None:
    calls: list[tuple[str, dict]] = []
    pipeline = types.SimpleNamespace(stop_dictation=lambda: calls.append(("pipeline.stop_dictation", {})))
    router = DictationRouter(_registry(calls, True), pipeline, _log([]))
    result = router.stop(_state())
    assert result.handled is True
    assert result.reply == "Dictation stopped."
    assert calls[-2:] == [("dictation.stop_dictation", {"session_id": "session-1"}), ("pipeline.stop_dictation", {})]


def _registry(calls: list[tuple[str, dict]], success: bool) -> object:
    def get(name: str) -> object:
        if name == "dictation.process_segment":
            return _tool(calls, name, ToolResult(True, "dictation updated", _segment()))
        if name == "dictation.stop_dictation":
            return _tool(calls, name, ToolResult(True, "dictation stopped"))
        if name == "gnome.get_active_window":
            return _tool(calls, name, ToolResult(True, "active window: Editor -> gedit"))
        return _tool(calls, name, ToolResult(success, "typed" if success else "typing failed"))

    return types.SimpleNamespace(get=get)


def _tool(calls: list[tuple[str, dict]], name: str, result: ToolResult) -> object:
    return types.SimpleNamespace(execute=lambda args: _record(calls, name, args, result))


def _record(calls: list[tuple[str, dict]], name: str, args: dict, result: ToolResult) -> ToolResult:
    calls.append((name, args))
    return result


def _segment() -> dict:
    return {"operation": "insert", "text": "hello world", "should_stop": False}


def _state() -> object:
    return types.SimpleNamespace(adapter_name="dictation", desktop_source="gnome", session_id="session-1")


def _log(logs: list[tuple[str, str]]) -> object:
    return types.SimpleNamespace(log=lambda group, message, source=None: logs.append((group, message)))


def _expected_logs() -> list[tuple[str, str]]:
    return [
        ("DICTATION", "segment='hello world'"),
        ("DICTATION", "active window: Editor -> gedit"),
        ("DICTATION", "apply insert via gnome"),
    ]
