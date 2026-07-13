import types

from tusk.kernel.core.agent_profiles import build_agent_profiles
from tusk.kernel.core.main_agent import MainAgent


def test_command_reply_with_tool_json_speaks_the_summary() -> None:
    wrapped = '[tool:done] {"status":"done","summary":"Opened gedit and pasted a poem."}'
    reply = _agent("done", wrapped).process_command("open gedit", "command")
    assert reply == "Opened gedit and pasted a poem."


def test_bare_json_reply_speaks_the_summary() -> None:
    reply = _agent("done", '{"summary":"Switched to PowerPoint."}').process_command("switch", "command")
    assert reply == "Switched to PowerPoint."


def test_failed_run_speaks_a_friendly_message() -> None:
    reply = _agent("failed", "repeated identical tool call").process_command("switch", "command")
    assert reply == "I couldn't complete that."


def test_plain_reply_is_spoken_unchanged() -> None:
    reply = _agent("done", "Opening gedit with a poem.").process_command("open gedit", "command")
    assert reply == "Opening gedit with a poem."


def test_non_string_json_summary_is_not_spoken_as_repr() -> None:
    reply = _agent("done", '{"summary": ["a", "b"]}').process_command("x", "command")
    assert reply != "['a', 'b']"


def test_command_prompt_forbids_tool_syntax_in_the_reply() -> None:
    prompt = build_agent_profiles(_registry()).get("command").system_prompt
    assert "plain spoken sentence" in prompt
    assert "JSON" in prompt


def _agent(status: str, reply_text: str) -> MainAgent:
    result = types.SimpleNamespace(status=status, session_id="c1", reply_text=lambda: reply_text)
    orchestrator = types.SimpleNamespace(run=lambda request: result)
    history = types.SimpleNamespace(append=lambda message: None)
    return MainAgent(orchestrator, history, None)


def _registry() -> object:
    return types.SimpleNamespace(get=lambda name: types.SimpleNamespace(label=name))
