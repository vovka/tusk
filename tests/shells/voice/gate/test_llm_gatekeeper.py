import types

from shells.voice.gate.llm_gatekeeper import LLMGatekeeper
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.utterance import Utterance


def test_gatekeeper_uses_structured_output() -> None:
    calls = []
    dispatch = _gatekeeper(calls=calls).process(_buffered("Tusk open Firefox"), [], [])
    assert calls and calls[0][2] == "command_gatekeeper"
    assert dispatch.action == "forward_current"
    assert dispatch.text == "open Firefox"
    assert dispatch.kind == "command"


def test_primary_schema_requires_intent_and_accepts_interrupt() -> None:
    calls = []
    _gatekeeper(calls=calls).process(_buffered("Tusk open Firefox"), [], [])
    schema = calls[0][3]
    assert "intent" in schema["properties"] and "intent" in schema["required"]
    assert "interrupt" in schema["properties"]["classification"]["enum"]


def test_gatekeeper_forwards_wake_word_conversation() -> None:
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda *a: _conversation())
    dispatch = LLMGatekeeper(llm, _log()).process(_buffered("Tusk, how are you?"), [], [])
    assert dispatch.action == "forward_current"
    assert dispatch.text == "how are you"
    assert dispatch.kind == "conversation"


def test_gatekeeper_drops_no_wake_conversation() -> None:
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda *a: _conversation())
    dispatch = LLMGatekeeper(llm, _log()).process(_buffered("Where are you going to go?"), [_utterance("open Firefox")], [])
    assert dispatch.action == "drop"
    assert dispatch.text is None


def test_gatekeeper_handles_wrapped_fenced_json() -> None:
    raw = '```json\n[{"arguments":{"classification":"ambient","cleaned_text":"","reason":"noise"}}]\n```'
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda *a: raw)
    assert LLMGatekeeper(llm, _log()).process(_buffered("noise"), [], []).action == "drop"


def test_gatekeeper_falls_back_when_structured_call_fails() -> None:
    llm = types.SimpleNamespace(label="gate", complete_structured=_structured_failure, complete=lambda *a: _command("tell me a joke"))
    dispatch = LLMGatekeeper(llm, _log()).process(_buffered("Great, tell me a joke, please."), [], [])
    assert dispatch.action == "forward_current"
    assert dispatch.text == "tell me a joke"


def test_gatekeeper_logs_result_summary() -> None:
    logs: list[tuple[str, str, str]] = []
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda *a: _command("open Firefox"))
    LLMGatekeeper(llm, _log(logs)).process(_buffered("Tusk open Firefox"), [], [])
    assert logs[-1] == (
        "GATEKEEPER",
        "classification=command directed=True text='open Firefox' reason='wake word'",
        "gatekeeper",
    )


def _gatekeeper(calls: list[tuple]) -> LLMGatekeeper:
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda *args: calls.append(args) or _command("open Firefox"))
    return LLMGatekeeper(llm, _log())


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _buffered(text: str) -> BufferedUtterance:
    return BufferedUtterance("u1", _utterance(text), 1.0)


def _log(logs: list[tuple[str, str, str]] | None = None) -> object:
    sink = logs if logs is not None else []
    return types.SimpleNamespace(log=lambda *args: sink.append(args))


def _command(cleaned_text: str) -> str:
    return f'{{"classification":"command","cleaned_text":"{cleaned_text}","reason":"wake word"}}'


def _conversation() -> str:
    return '{"classification":"conversation","cleaned_text":"how are you","reason":"addressed to tusk"}'


def _structured_failure(*args) -> str:
    raise RuntimeError("json_validate_failed")
