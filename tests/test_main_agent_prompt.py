import types

from tests.kernel_api_support import make_agent, make_registry_tool
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_main_agent_sends_command_history_without_desktop_context() -> None:
    capture: dict[str, object] = {}
    llm = types.SimpleNamespace(label="agent", complete_tool_call=_capture_completion(capture))
    make_agent(llm).process_command("open gedit")
    assert capture["messages"] == [{"role": "user", "content": "Command: open gedit"}]


def test_main_agent_sends_visible_tools_as_native_definitions() -> None:
    capture: dict[str, object] = {}
    registry = ToolRegistry()
    registry.register(make_registry_tool("find_tools", "discover", broker=True, prompt_visible=True))
    registry.register(make_registry_tool("gnome.type_text", "type", prompt_visible=True))
    registry.register(make_registry_tool("gnome.list_windows", "list", prompt_visible=False))
    llm = types.SimpleNamespace(label="agent", complete_tool_call=_capture_prompt(capture))
    make_agent(llm, registry=registry).process_command("type hello")
    names = [item["function"]["name"] for item in capture["tools"]]
    assert "find_tools" in names and "gnome.type_text" not in names and "gnome.list_windows" not in names


def test_main_agent_prompt_explains_broker_and_key_rules() -> None:
    capture: dict[str, object] = {}
    llm = types.SimpleNamespace(label="agent", complete_tool_call=_capture_prompt(capture))
    make_agent(llm).process_command("press enter")
    prompt = str(capture["prompt"])
    assert "Available tool names" in prompt
    assert "If you want to use a tool and it has not already been described" in prompt
    assert "Never use type_text for Enter" in prompt
    assert "input_json string" in prompt
    assert "Example workflow" in prompt
    assert "call describe_tool with its name" in prompt


def _capture_completion(capture: dict[str, object]) -> object:
    def complete(prompt, messages, tools):
        capture["messages"] = [dict(item) for item in messages]
        capture["tools"] = list(tools)
        return ToolCall("done", {"reply": "Finished."}, "call-1")

    return complete


def _capture_prompt(capture: dict[str, object]) -> object:
    def complete(prompt, messages, tools):
        capture["prompt"] = prompt
        capture["tools"] = list(tools)
        return ToolCall("done", {"reply": "Finished."}, "call-1")

    return complete
