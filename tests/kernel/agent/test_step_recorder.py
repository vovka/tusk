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


def _recorder() -> StepRecorder:
    return StepRecorder(types.SimpleNamespace())
