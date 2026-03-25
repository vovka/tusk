import types

from tusk.kernel.agent import MainAgent
from tusk.kernel.schemas.desktop_context import DesktopContext
from tusk.kernel.tool_registry import ToolRegistry


def test_clarify_stops_agent_loop_and_persists_reply() -> None:
    stored = []
    history = types.SimpleNamespace(
        append=lambda message: stored.append((message.role, message.content)),
        get_messages=lambda: [],
    )
    llm = types.SimpleNamespace(
        label="agent",
        complete_messages=lambda *a: '{"tool":"clarify","reply":"What exactly should I open?"}',
    )
    agent = MainAgent(
        llm,
        ToolRegistry(),
        history,
        types.SimpleNamespace(get_context=lambda: DesktopContext("", "")),
        types.SimpleNamespace(log=lambda *a: None),
    )
    reply = agent.process_command("open it")
    assert reply == "What exactly should I open?"
    assert stored == [
        ("user", "Command: open it"),
        ("assistant", "What exactly should I open?"),
    ]
