import types

from tests.kernel_api_support import make_agent, make_registry_tool
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_main_agent_prompt_exposes_only_finish_and_run_agent() -> None:
    capture: dict[str, object] = {}
    llm = types.SimpleNamespace(label="conversation", complete_tool_call=_capture_prompt(capture))
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type"))
    make_agent(llm, registry=registry).process_command("type hello")
    names = [item["function"]["name"] for item in capture["tools"]]
    assert names == ["done", "run_agent"]


def test_main_agent_prompt_mentions_planner_and_executor_flow() -> None:
    capture: dict[str, object] = {}
    llm = types.SimpleNamespace(label="conversation", complete_tool_call=_capture_prompt(capture))
    make_agent(llm).process_command("press enter")
    prompt = str(capture["prompt"])
    assert "general knowledge" in prompt
    assert "planner profile" in prompt
    assert "executor profile" in prompt
    assert "Use done" in prompt


def _capture_prompt(capture: dict[str, object]) -> object:
    def complete(prompt, messages, tools):
        capture["prompt"] = prompt
        capture["messages"] = [dict(item) for item in messages]
        capture["tools"] = list(tools)
        return ToolCall("done", {"status": "done", "summary": "Finished.", "text": "Finished."}, "call-1")

    return complete
