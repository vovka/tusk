import types

from tests.support.kernel_api import make_agent, make_registry_tool
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_call import ToolCall


def test_command_llm_failure_after_successful_tool_keeps_progress() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("kernel.start_coding", "Coding mode started."))
    llm = types.SimpleNamespace(label="command", complete_tool_call=_start_then_fail())
    reply = make_agent(llm, registry=registry).process_command("start pair coding", "command")
    assert reply == "Coding mode started."


def _start_then_fail() -> object:
    calls = iter([ToolCall("call_tool", {"name": "kernel.start_coding", "arguments": {}}, "call-1")])

    def complete_tool_call(*args: object) -> ToolCall:
        call = next(calls, None)
        if call is None:
            raise RuntimeError("rate limited")
        return call
    return complete_tool_call
