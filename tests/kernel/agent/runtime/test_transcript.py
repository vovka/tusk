import types

from tests.support.kernel_api import make_registry_tool
from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.runtime.transcript import Transcript
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult

_DONE_NUDGE = " Call the done tool now if the command is complete."


def test_appended_tolerates_non_dict_child_result_data() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "raw output", ["not", "a", "dict"])
    _transcript().appended(messages, ToolCall("coding.apply", {}, "c1"), result)
    assert messages[-1] == {"role": "user", "content": "raw output"}


def test_appended_skips_clipboard_message_for_non_dict_data() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "written", ["clipboard_text"])
    _transcript().appended(messages, ToolCall("gnome.write_clipboard", {}, "c1"), result)
    assert all("[clipboard-written]" not in item["content"] for item in messages)


def test_appended_truncates_long_tool_result_message() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(False, "x" * 2000, None)
    _transcript().appended(messages, ToolCall("gnome.press_keys", {}, "c1"), result)
    content = messages[-1]["content"]
    assert content == "x" * 500 + "…[truncated]"


def test_appended_keeps_short_tool_result_message_intact() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "x" * 500, None)
    _transcript().appended(messages, ToolCall("gnome.press_keys", {}, "c1"), result)
    assert messages[-1]["content"] == "x" * 500


def test_appended_keeps_long_successful_message_intact() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "x" * 2000, None)
    _transcript().appended(messages, ToolCall("gnome.read_clipboard", {}, "c1"), result)
    assert messages[-1]["content"] == "x" * 2000


def test_appended_tolerates_missing_tool_result_message() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(False, None, None)
    _transcript().appended(messages, ToolCall("gnome.press_keys", {}, "c1"), result)
    assert messages[-1]["content"] == ""


def test_appended_nudges_done_after_successful_actuator() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "maximized", None)
    transcript = _transcript({"gnome.maximize_window"})
    transcript.appended(messages, ToolCall("gnome.maximize_window", {}, "c1"), result)
    assert messages[-1] == {"role": "user", "content": "maximized" + _DONE_NUDGE}


def test_appended_skips_nudge_for_read_only_tool() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "desktop context", None)
    transcript = _transcript({"gnome.maximize_window"})
    transcript.appended(messages, ToolCall("gnome.get_desktop_context", {}, "c1"), result)
    assert messages[-1] == {"role": "user", "content": "desktop context"}


def test_appended_skips_nudge_for_failed_actuator() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(False, "boom", None)
    transcript = _transcript({"gnome.maximize_window"})
    transcript.appended(messages, ToolCall("gnome.maximize_window", {}, "c1"), result)
    assert messages[-1] == {"role": "user", "content": "boom"}


def test_appended_skips_nudge_for_unknown_tool() -> None:
    messages: list[dict[str, str]] = []
    result = ToolResult(True, "ok", None)
    registry = types.SimpleNamespace(get=_raise_key_error, resolve_name=lambda name: name)
    transcript = Transcript(types.SimpleNamespace(), registry)
    transcript.appended(messages, ToolCall("gnome.unregistered_tool", {}, "c1"), result)
    assert messages[-1] == {"role": "user", "content": "ok"}


def _raise_key_error(name: str) -> object:
    raise KeyError(name)


def test_result_event_keeps_full_message() -> None:
    events: list[tuple[str, str, dict]] = []
    store = types.SimpleNamespace(append_event=lambda sid, name, data: events.append((sid, name, data)))
    registry = types.SimpleNamespace()
    result = ToolResult(False, "x" * 2000, None)
    Transcript(store, registry).result("s1", 1, ToolCall("gnome.press_keys", {}, "c1"), result)
    assert events[0][2]["message"] == "x" * 2000


def _transcript(sequence_tools: set[str] | None = None) -> Transcript:
    tools = sequence_tools or set()
    registry = types.SimpleNamespace(
        get=lambda name: types.SimpleNamespace(sequence_callable=name in tools), resolve_name=lambda name: name,
    )
    return Transcript(types.SimpleNamespace(), registry)


def test_appended_tool_call_keeps_its_arguments() -> None:
    # without the arguments gpt-oss could not tell what it already did and re-issued the call until max steps
    messages: list[dict[str, str]] = []
    call = ToolCall("switch_model", {"slot": "main_agent", "model": "gpt-oss-120b"}, "c1")
    _transcript().appended(messages, call, ToolResult(True, "switched"))
    assert messages[0]["content"] == '[tool:switch_model] called with {"slot": "main_agent", "model": "gpt-oss-120b"}'


def test_appended_nudges_done_after_actuator_called_by_short_name() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.launch_application", "launched", sequence_callable=True))
    messages: list[dict[str, str]] = []
    Transcript(types.SimpleNamespace(), registry).appended(messages, ToolCall("launch_application", {}), ToolResult(True, "ok"))
    assert "Call the done tool now" in messages[-1]["content"]


def test_build_returns_prior_messages_followed_by_session_ref_digests() -> None:
    store = types.SimpleNamespace(
        conversation_messages=lambda sid: [{"role": "user", "content": "earlier"}],
        session_digest=lambda ref: {"s2": "child did x"}.get(ref, ""),
    )
    messages = Transcript(store, types.SimpleNamespace()).build("s1", AgentRunRequest("do", session_refs=("s2", "s3")))
    assert messages == [
        {"role": "user", "content": "earlier"},
        {"role": "user", "content": "[session-ref] child did x"},
    ]
