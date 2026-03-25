import types

from tests.kernel_api_support import make_agent, make_registry_tool
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_main_agent_sends_command_history_without_desktop_context() -> None:
    capture: dict[str, object] = {}
    llm = types.SimpleNamespace(label="agent", complete_tool_call=_capture_completion(capture))
    make_agent(llm).process_command("open gedit")
    assert capture["messages"] == [{"role": "user", "content": "Command: open gedit"}]


def test_main_agent_sends_only_execute_task_as_operational_tool() -> None:
    capture: dict[str, object] = {}
    registry = ToolRegistry()
    registry.register(make_registry_tool("execute_task", "execute", planner_visible=False, input_schema=_task_schema()))
    registry.register(make_registry_tool("gnome.type_text", "type"))
    registry.register(make_registry_tool("gnome.list_windows", "list"))
    llm = types.SimpleNamespace(label="agent", complete_tool_call=_capture_prompt(capture))
    make_agent(llm, registry=registry).process_command("type hello")
    names = [item["function"]["name"] for item in capture["tools"]]
    assert "execute_task" in names and "gnome.type_text" not in names and "gnome.list_windows" not in names


def test_main_agent_prompt_explains_execute_task_routing() -> None:
    capture: dict[str, object] = {}
    llm = types.SimpleNamespace(label="agent", complete_tool_call=_capture_prompt(capture))
    make_agent(llm).process_command("press enter")
    prompt = str(capture["prompt"])
    assert "Use execute_task for requests that require actions" in prompt
    assert "Use done for conversational replies" in prompt
    assert "execute_task" in prompt
    assert "describe_tool" not in prompt
    assert "Available tool names" not in prompt


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


def _task_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {"task": {"type": "string"}},
        "required": ["task"],
        "additionalProperties": False,
    }
