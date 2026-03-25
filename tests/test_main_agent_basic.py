import types

from tests.kernel_api_support import HistoryRecorder, make_agent


def test_main_agent_returns_final_reply() -> None:
    agent = make_agent(types.SimpleNamespace(label="agent", complete_messages=lambda *args: '{"tool":"done","reply":"Finished."}'))
    assert agent.process_command("test") == "Finished."


def test_main_agent_invalid_json_returns_visible_failure() -> None:
    logs: list[tuple[str, str]] = []
    llm = types.SimpleNamespace(label="agent", complete_messages=lambda *args: "sure, I can do that")
    log = types.SimpleNamespace(log=lambda tag, message: logs.append((tag, message)))
    reply = make_agent(llm, log=log).process_command("test")
    assert reply == "I could not interpret the model response."
    assert any(tag == "AGENT" and "invalid JSON" in message for tag, message in logs)


def test_main_agent_handles_rate_limit_without_crashing() -> None:
    llm = types.SimpleNamespace(label="agent", complete_messages=lambda *args: (_ for _ in ()).throw(RuntimeError("Rate limit reached")))
    logs: list[tuple[str, str]] = []
    log = types.SimpleNamespace(log=lambda tag, message, *rest: logs.append((tag, message)))
    reply = make_agent(llm, log=log).process_command("tell me a joke")
    assert "rate limited" in reply.lower()
    assert any(tag == "AGENT" and "llm failure" in message for tag, message in logs)


def test_clarify_stops_agent_loop_and_persists_reply() -> None:
    history = HistoryRecorder()
    llm = types.SimpleNamespace(label="agent", complete_messages=lambda *a: '{"tool":"clarify","reply":"What exactly should I open?"}')
    reply = make_agent(llm, history=history).process_command("open it")
    assert reply == "What exactly should I open?"
    assert history.stored == [("user", "Command: open it"), ("assistant", "What exactly should I open?")]
