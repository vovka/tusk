import types

from tests.kernel_api_support import make_agent, make_registry_tool
from tusk.shared.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_executor_blocks_clipboard_rewrite_before_paste() -> None:
    reply = make_agent(_delegate_once(), registry=_clipboard_registry(), executor_llm=_rewriting_executor()).process_command("test")
    assert "must not change clipboard text before paste" in reply.lower()


def test_executor_allows_intermediate_actions_before_paste() -> None:
    reply = make_agent(_delegate_once(), registry=_clipboard_registry(), executor_llm=_clipboard_then_paste()).process_command("test")
    assert "child_status: done" in reply
    assert "child_summary: pasted" in reply


def test_executor_blocks_copy_shortcut_before_paste() -> None:
    reply = make_agent(_delegate_once(), registry=_clipboard_registry(), executor_llm=_copying_executor()).process_command("test")
    assert "must not copy to clipboard again before paste" in reply.lower()


def _delegate_once() -> object:
    state = {"step": 0}
    params = {"profile_id": "executor", "instruction": "paste", "runtime_tool_names": ["gnome.write_clipboard", "gnome.focus_window", "gnome.press_keys"]}

    def complete(prompt, messages, tools):
        state["step"] += 1
        if state["step"] == 1:
            return ToolCall("run_agent", params, "c1")
        return ToolCall("done", {"status": "done", "summary": "done", "text": messages[-1]["content"]}, "c2")

    return types.SimpleNamespace(label="conversation", complete_tool_call=complete)


def _clipboard_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.write_clipboard", "clipboard written"))
    registry.register(make_registry_tool("gnome.focus_window", "focused"))
    registry.register(make_registry_tool("gnome.press_keys", "pressed"))
    return registry


def _rewriting_executor() -> object:
    state = {"step": 0}

    def complete(prompt, messages, tools):
        state["step"] += 1
        text = "draft one" if state["step"] == 1 else "draft two"
        return ToolCall("gnome.write_clipboard", {"text": text}, f"e{state['step']}")

    return types.SimpleNamespace(label="executor", complete_tool_call=complete)


def _clipboard_then_paste() -> object:
    state = {"step": 0}

    def complete(prompt, messages, tools):
        state["step"] += 1
        return _clipboard_step(state["step"])

    return types.SimpleNamespace(label="executor", complete_tool_call=complete)


def _clipboard_step(step: int) -> ToolCall:
    if step == 1:
        return ToolCall("gnome.write_clipboard", {"text": "draft"}, "e1")
    if step == 2:
        return ToolCall("gnome.focus_window", {"window_title": "gedit"}, "e2")
    if step == 3:
        return ToolCall("gnome.press_keys", {"keys": "<ctrl>l"}, "e3")
    if step == 4:
        return ToolCall("gnome.press_keys", {"keys": "<ctrl>v"}, "e4")
    return ToolCall("done", {"status": "done", "summary": "pasted", "text": "pasted"}, "e5")


def _copying_executor() -> object:
    state = {"step": 0}

    def complete(prompt, messages, tools):
        state["step"] += 1
        if state["step"] < 3:
            return ToolCall("gnome.press_keys", {"keys": "<ctrl>c"}, f"e{state['step']}")
        return ToolCall("done", {"status": "done", "summary": "pasted", "text": "pasted"}, "e4")

    return types.SimpleNamespace(label="executor", complete_tool_call=complete)
