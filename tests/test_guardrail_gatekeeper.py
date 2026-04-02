import types

from shells.voice.stages.gatekeeper import LLMGatekeeper
from tusk.shared.schemas.utterance import Utterance


def test_gatekeeper_uses_structured_output() -> None:
    calls = []
    result = _gatekeeper(calls=calls).evaluate(_utterance("Tusk open Firefox"), [])
    assert calls and calls[0][2] == "command_gatekeeper"
    assert result.is_directed_at_tusk
    assert result.cleaned_command == "open Firefox"
    assert result.metadata["classification"] == "command"


def test_gatekeeper_treats_conversation_as_directed() -> None:
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda *a: _conversation())
    result = LLMGatekeeper(llm, _log()).evaluate(_utterance("Tusk, how are you?"), [])
    assert result.is_directed_at_tusk
    assert result.metadata["classification"] == "conversation"


def test_gatekeeper_handles_wrapped_fenced_json() -> None:
    raw = '```json\n[{"arguments":{"classification":"ambient","cleaned_text":"","reason":"noise"}}]\n```'
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda *a: raw)
    result = LLMGatekeeper(llm, _log()).evaluate(_utterance("noise"), [])
    assert not result.is_directed_at_tusk
    assert result.metadata["classification"] == "ambient"


def test_gatekeeper_falls_back_when_structured_call_fails() -> None:
    llm = types.SimpleNamespace(label="gate", complete_structured=_structured_failure, complete=lambda *a: _command("tell me a joke"))
    result = LLMGatekeeper(llm, _log()).evaluate(_utterance("Great, tell me a joke, please."), [])
    assert result.is_directed_at_tusk
    assert result.cleaned_command == "tell me a joke"


def _gatekeeper(calls: list[tuple]) -> LLMGatekeeper:
    llm = types.SimpleNamespace(label="gate", complete_structured=lambda *args: calls.append(args) or _command("open Firefox"))
    return LLMGatekeeper(llm, _log())


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)


def _command(cleaned_text: str) -> str:
    return f'{{"classification":"command","cleaned_text":"{cleaned_text}","reason":"wake word"}}'


def _conversation() -> str:
    return '{"classification":"conversation","cleaned_text":"how are you","reason":"addressed to tusk"}'


def _structured_failure(*args) -> str:
    raise RuntimeError("json_validate_failed")
