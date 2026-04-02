import types

from tests.kernel_api_support import make_agent, make_registry_tool
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_registry import ToolRegistry


def test_conversation_stops_after_two_failed_executor_runs() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed"))
    reply = make_agent(_retrying_conversation(), registry=registry, executor_llm=_failed_executor()).process_command("test")
    assert "retry budget" in reply.lower()


def _retrying_conversation() -> object:
    params = {"profile_id": "executor", "instruction": "retry", "runtime_tool_names": ["gnome.type_text"]}
    return types.SimpleNamespace(label="conversation", complete_tool_call=lambda *a: ToolCall("run_agent", params, "c1"))


def _failed_executor() -> object:
    return types.SimpleNamespace(
        label="executor",
        complete_tool_call=lambda *a: ToolCall("done", {"status": "failed", "summary": "boom", "text": "boom"}, "e1"),
    )
