import types

from tests.kernel_api_support import HistoryRecorder, make_agent
from tusk.shared.interrupt import InterruptToken
from tusk.shared.schemas.tools.tool_call import ToolCall


def test_interrupt_cancels_run_at_next_step_boundary() -> None:
    token = InterruptToken()
    calls = {"count": 0}
    llm = _interrupting_llm(token, calls)
    reply = make_agent(llm, interrupt_token=token).process_command("slow task")
    assert reply == "Stopped."
    assert calls["count"] == 1


def test_preset_token_cancels_before_any_llm_call() -> None:
    token = InterruptToken()
    token.interrupt()
    calls = {"count": 0}
    llm = _finishing_llm(calls)
    reply = make_agent(llm, interrupt_token=token).process_command("task")
    assert reply == "Stopped."
    assert calls["count"] == 0


def test_history_records_cancelled_turn() -> None:
    token = InterruptToken()
    token.interrupt()
    llm = types.SimpleNamespace(
        label="conversation",
        complete_tool_call=lambda *args: ToolCall("done", {"status": "done", "summary": "done"}, "c1"),
    )
    history = HistoryRecorder()
    make_agent(llm, history=history, interrupt_token=token).process_command("task")
    assert ("assistant", "Stopped.") in history.stored


def _interrupting_llm(token: InterruptToken, calls: dict) -> object:
    def complete(prompt, messages, tools):
        calls["count"] += 1
        token.interrupt()
        return ToolCall("list_available_tools", {}, "c1")
    return types.SimpleNamespace(label="conversation", complete_tool_call=complete)


def _finishing_llm(calls: dict) -> object:
    def complete(prompt, messages, tools):
        calls["count"] += 1
        return ToolCall("done", {"status": "done", "summary": "done", "text": "hi"}, "c1")
    return types.SimpleNamespace(label="conversation", complete_tool_call=complete)
