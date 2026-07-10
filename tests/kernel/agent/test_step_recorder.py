import types

from tusk.kernel.agent.runtime.step_recorder import StepRecorder
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult


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


def test_result_event_keeps_full_message() -> None:
    events: list[tuple[str, str, dict]] = []
    store = types.SimpleNamespace(append_event=lambda sid, name, data: events.append((sid, name, data)))
    result = ToolResult(False, "x" * 2000, None)
    StepRecorder(store).result("s1", 1, ToolCall("gnome.press_keys", {}, "c1"), result)
    assert events[0][2]["message"] == "x" * 2000


def _recorder() -> StepRecorder:
    return StepRecorder(types.SimpleNamespace())
