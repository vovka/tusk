from tests.kernel_api_support import HistoryRecorder, make_agent, make_registry_tool
from tusk.shared.interrupt import InterruptToken
from tusk.shared.schemas.tool_call import ToolCall
from tusk.shared.schemas.tool_result import ToolResult
from tusk.kernel.tool_registry import ToolRegistry


def test_agent_runtime_cancels_before_next_llm_step() -> None:
    token = InterruptToken()
    calls: list[str] = []
    history = HistoryRecorder()
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "typed", execute=_interrupt(token)))
    reply = make_agent(_llm(calls), history, registry=registry, interrupt_token=token).process_command("test")
    assert reply == "Stopped."
    assert calls == ["llm"]
    assert history.stored[-1] == ("assistant", "Stopped.")


def _llm(calls: list[str]) -> object:
    def complete_tool_call(*args: object) -> ToolCall:
        calls.append("llm")
        return ToolCall("gnome.type_text", {"text": "hello"}, "c1")

    return type("LLM", (), {"label": "conversation", "complete_tool_call": complete_tool_call})()


def _interrupt(token: InterruptToken) -> object:
    def execute(arguments: dict[str, object]) -> ToolResult:
        token.interrupt()
        return ToolResult(True, "typed")

    return execute
