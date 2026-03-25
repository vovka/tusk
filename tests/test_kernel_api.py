import types

from tusk.kernel.agent import MainAgent
from tusk.kernel.api import KernelAPI
from tusk.kernel.schemas.desktop_context import DesktopContext
from tusk.kernel.schemas.kernel_response import KernelResponse
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry


def test_tool_registry_renders_json_schema_text() -> None:
    registry = ToolRegistry()
    tool = types.SimpleNamespace(
        name="gnome.close_window",
        description="Close a window",
        input_schema={"type": "object", "properties": {"window_title": {"type": "string"}}},
        execute=lambda _: ToolResult(True, "closed"),
        source="gnome",
    )
    registry.register(tool)
    text = registry.build_schema_text()
    assert "Tool: gnome.close_window" in text
    assert '"window_title"' in text


def test_main_agent_returns_final_reply() -> None:
    llm = types.SimpleNamespace(
        label="agent",
        complete_messages=lambda *args: '{"tool":"done","reply":"Finished."}',
    )
    history = types.SimpleNamespace(
        append=lambda message: None,
        get_messages=lambda: [],
    )
    agent = MainAgent(llm, ToolRegistry(), history, types.SimpleNamespace(get_context=lambda: DesktopContext("", "")), types.SimpleNamespace(log=lambda *a: None))
    assert agent.process_command("test") == "Finished."


def test_main_agent_invalid_json_returns_visible_failure() -> None:
    llm = types.SimpleNamespace(
        label="agent",
        complete_messages=lambda *args: "sure, I can do that",
    )
    history = types.SimpleNamespace(
        append=lambda message: None,
        get_messages=lambda: [],
    )
    logs: list[tuple[str, str]] = []
    agent = MainAgent(
        llm,
        ToolRegistry(),
        history,
        types.SimpleNamespace(get_context=lambda: DesktopContext("", "")),
        types.SimpleNamespace(log=lambda tag, message: logs.append((tag, message))),
    )
    reply = agent.process_command("test")
    assert reply == "I could not interpret the model response."
    assert any(tag == "AGENT" and "invalid JSON" in message for tag, message in logs)


def test_main_agent_sends_context_as_transient_payload() -> None:
    capture = {}

    def complete_messages(prompt, messages):
        capture["messages"] = messages
        return '{"tool":"done","reply":"Finished."}'

    llm = types.SimpleNamespace(label="agent", complete_messages=complete_messages)
    history = types.SimpleNamespace(append=lambda message: None, get_messages=lambda: [])
    context = DesktopContext(
        "Editor",
        "",
        available_applications=[types.SimpleNamespace(name=f"app-{index}") for index in range(100)],
    )
    agent = MainAgent(
        llm,
        ToolRegistry(),
        history,
        types.SimpleNamespace(get_context=lambda: context),
        types.SimpleNamespace(log=lambda *a: None),
    )
    agent.process_command("open gedit")
    assert capture["messages"][0]["content"].startswith("Desktop context:")
    assert capture["messages"][1]["content"] == "Command: open gedit"
    assert "... and 60 more" in capture["messages"][0]["content"]


def test_main_agent_persists_only_command_and_final_reply() -> None:
    stored = []

    class History:
        def append(self, message) -> None:
            stored.append((message.role, message.content))

        def get_messages(self):
            return []

    responses = iter([
        '{"tool":"gnome.launch_application","reply":"Opening gedit.","application_name":"gedit"}',
        '{"tool":"done","reply":"gedit is now open."}',
    ])
    llm = types.SimpleNamespace(label="agent", complete_messages=lambda *args: next(responses))
    registry = ToolRegistry()
    registry.register(
        types.SimpleNamespace(
            name="gnome.launch_application",
            description="Open an app",
            input_schema={"type": "object"},
            execute=lambda _: ToolResult(True, "launched: gedit"),
            source="gnome",
        )
    )
    agent = MainAgent(
        llm,
        registry,
        History(),
        types.SimpleNamespace(get_context=lambda: DesktopContext("", "")),
        types.SimpleNamespace(log=lambda *a: None),
    )
    reply = agent.process_command("open gedit")
    assert reply == "gedit is now open."
    assert stored == [
        ("user", "Command: open gedit"),
        ("assistant", "gedit is now open."),
    ]


def test_kernel_api_submit_text_bypasses_gatekeeper() -> None:
    pipeline = types.SimpleNamespace(process_text_command=lambda text: KernelResponse(True, f"ok: {text}"))
    api = KernelAPI(pipeline, types.SimpleNamespace(), types.SimpleNamespace(log=lambda *a: None))
    result = api.submit_text("open terminal")
    assert result == KernelResponse(True, "ok: open terminal")
