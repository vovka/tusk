import types

from tests.kernel_api_support import HistoryRecorder, make_context, make_registry_tool
from tusk.kernel.agent import MainAgent
from tusk.kernel.schemas.desktop_context import DesktopContext
from tusk.kernel.tool_registry import ToolRegistry


def test_main_agent_sends_context_as_transient_payload() -> None:
    capture: dict[str, object] = {}
    llm = types.SimpleNamespace(label="agent", complete_messages=_capture_completion(capture))
    context = types.SimpleNamespace(get_context=lambda: make_context("Editor", 100))
    MainAgent(llm, ToolRegistry(), HistoryRecorder(), context, types.SimpleNamespace(log=lambda *a: None)).process_command("open gedit")
    messages = capture["messages"]
    assert messages[0]["content"].startswith("Desktop context:")
    assert messages[1]["content"] == "Command: open gedit"
    assert "... and 60 more" in messages[0]["content"]


def test_main_agent_persists_only_command_and_final_reply() -> None:
    history = HistoryRecorder()
    responses = iter(_responses())
    llm = types.SimpleNamespace(label="agent", complete_messages=lambda *args: next(responses))
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.launch_application", "launched: gedit"))
    context = types.SimpleNamespace(get_context=lambda: DesktopContext("", ""))
    reply = MainAgent(llm, registry, history, context, types.SimpleNamespace(log=lambda *a: None)).process_command("open gedit")
    assert reply == "gedit is now open."
    assert history.stored == [("user", "Command: open gedit"), ("assistant", "gedit is now open.")]


def _capture_completion(capture: dict[str, object]) -> object:
    def complete(prompt, messages):
        capture["messages"] = messages
        return '{"tool":"done","reply":"Finished."}'

    return complete


def _responses() -> list[str]:
    return [
        '{"tool":"gnome.launch_application","reply":"Opening gedit.","application_name":"gedit"}',
        '{"tool":"done","reply":"gedit is now open."}',
    ]
