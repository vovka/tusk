from tusk.kernel.agent.guards.repeated_tool_call_guard import RepeatedToolCallGuard
from tusk.shared.schemas.tools.tool_call import ToolCall


def test_third_identical_call_is_repeated() -> None:
    guard = RepeatedToolCallGuard()
    call = ToolCall("gnome.type_text", {"text": "hi"}, "c1")
    assert [guard.repeated(call), guard.repeated(call), guard.repeated(call)] == [False, False, True]


def test_different_call_resets_count() -> None:
    guard = RepeatedToolCallGuard()
    call = ToolCall("gnome.type_text", {"text": "hi"}, "c1")
    guard.repeated(call)
    guard.repeated(call)
    guard.repeated(ToolCall("done", {}, "c2"))
    assert guard.repeated(call) is False
