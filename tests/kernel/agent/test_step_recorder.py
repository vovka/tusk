import types

from tusk.kernel.agent.runtime.step_recorder import StepRecorder
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult

_DONE_NUDGE = " Call the done tool now if the command is complete."


def test_appended_tolerates_non_dict_child_result_data() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "raw output", ["not", "a", "dict"])
    _recorder().appended(messages, ToolCall("coding.apply", {}, "c1"), result)
    assert messages[-1] == {"role": "user", "content": "raw output"}


def test_appended_skips_clipboard_message_for_non_dict_data() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "written", ["clipboard_text"])
    _recorder().appended(messages, ToolCall("gnome.write_clipboard", {}, "c1"), result)
    assert all("[clipboard-written]" not in item["content"] for item in messages)


def test_appended_truncates_long_tool_result_message() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(False, "x" * 2000, None)
    _recorder().appended(messages, ToolCall("gnome.press_keys", {}, "c1"), result)
    content = messages[-1]["content"]
    assert content == "x" * 500 + "…[truncated]"


def test_appended_keeps_short_tool_result_message_intact() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "x" * 500, None)
    _recorder().appended(messages, ToolCall("gnome.press_keys", {}, "c1"), result)
    assert messages[-1]["content"] == "x" * 500


def test_appended_keeps_long_successful_message_intact() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "x" * 2000, None)
    _recorder().appended(messages, ToolCall("gnome.read_clipboard", {}, "c1"), result)
    assert messages[-1]["content"] == "x" * 2000


def test_appended_tolerates_missing_tool_result_message() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(False, None, None)
    _recorder().appended(messages, ToolCall("gnome.press_keys", {}, "c1"), result)
    assert messages[-1]["content"] == ""


def test_appended_nudges_done_after_successful_actuator() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "maximized", None)
    recorder = _recorder({"gnome.maximize_window"})
    recorder.appended(messages, ToolCall("gnome.maximize_window", {}, "c1"), result)
    assert messages[-1] == {"role": "user", "content": "maximized" + _DONE_NUDGE}


def test_appended_skips_nudge_for_read_only_tool() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "desktop context", None)
    recorder = _recorder({"gnome.maximize_window"})
    recorder.appended(messages, ToolCall("gnome.get_desktop_context", {}, "c1"), result)
    assert messages[-1] == {"role": "user", "content": "desktop context"}


def test_appended_skips_nudge_for_failed_actuator() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(False, "boom", None)
    recorder = _recorder({"gnome.maximize_window"})
    recorder.appended(messages, ToolCall("gnome.maximize_window", {}, "c1"), result)
    assert messages[-1] == {"role": "user", "content": "boom"}


def test_appended_skips_nudge_for_unknown_tool() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "ok", None)
    registry = types.SimpleNamespace(get=_raise_key_error)
    recorder = StepRecorder(types.SimpleNamespace(), registry)
    recorder.appended(messages, ToolCall("gnome.unregistered_tool", {}, "c1"), result)
    assert messages[-1] == {"role": "user", "content": "ok"}


def _raise_key_error(name: str) -> object:
    raise KeyError(name)


def test_result_event_keeps_full_message() -> None:
    events: list[tuple[str, str, dict]] = []
    store = types.SimpleNamespace(append_event=lambda sid, name, data: events.append((sid, name, data)))
    registry = types.SimpleNamespace(sequence_tool_names=lambda: set())
    result = ToolResult(False, "x" * 2000, None)
    StepRecorder(store, registry).result("s1", 1, ToolCall("gnome.press_keys", {}, "c1"), result)
    assert events[0][2]["message"] == "x" * 2000


def _recorder(sequence_tools: set[str] | None = None) -> StepRecorder:
    tools = sequence_tools or set()
    registry = types.SimpleNamespace(get=lambda name: types.SimpleNamespace(sequence_callable=name in tools))
    return StepRecorder(types.SimpleNamespace(), registry)
