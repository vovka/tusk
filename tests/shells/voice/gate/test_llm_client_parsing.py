import types

from shells.voice.gate.llm_client import LLMClient
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.utterance import Utterance

_PAYLOAD = '{"classification": "command", "cleaned_text": "open firefox", "reason": "direct"}'


def test_parses_plain_json() -> None:
    result = _client(_PAYLOAD).primary("prompt", "text")
    assert result.classification == "command"
    assert result.cleaned_command == "open firefox"
    assert result.is_directed_at_tusk


def test_parses_fenced_json_with_surrounding_prose() -> None:
    result = _client(f"Sure, here it is:\n```json\n{_PAYLOAD}\n```\nLet me know!").primary("prompt", "text")
    assert result.classification == "command"


def test_parses_arguments_wrapped_list_json() -> None:
    result = _client(f'[{{"arguments": {_PAYLOAD}}}]').primary("prompt", "text")
    assert result.cleaned_command == "open firefox"


def test_unknown_classification_falls_back_to_ambient() -> None:
    result = _client('{"classification": "banana", "cleaned_text": ""}').primary("prompt", "text")
    assert result.classification == "ambient"
    assert not result.is_directed_at_tusk


def test_parses_intent_refrain_and_defaults_it_empty() -> None:
    payload = '{"classification": "command", "cleaned_text": "open firefox", "intent": "Opening Firefox"}'
    assert _client(payload).primary("prompt", "text").intent == "Opening Firefox"
    assert _client(_PAYLOAD).primary("prompt", "text").intent == ""


def test_parses_recovery_decision_embedded_in_prose() -> None:
    raw = 'Decision: {"action": "recover", "candidate_id": "u2", "reason": "match"} done.'
    decision = _client(raw).recovery("prompt", "text", [_candidate("u2")])
    assert (decision.action, decision.candidate_id) == ("recover", "u2")


def test_recovery_of_unknown_candidate_becomes_none() -> None:
    raw = '{"action": "recover", "candidate_id": "u9", "reason": "match"}'
    decision = _client(raw).recovery("prompt", "text", [_candidate("u2")])
    assert decision.action == "none"
    assert decision.reason == "invalid candidate"


def test_complete_returns_empty_payload_on_parse_error() -> None:
    tags: list[str] = []
    log = types.SimpleNamespace(log=lambda tag, *a: tags.append(tag))
    llm = types.SimpleNamespace(complete_structured=lambda *a: "no json here")
    assert LLMClient(llm, log).complete("prompt", "text", "name", {}) == {}
    assert tags == ["ERROR"]


def _client(raw: str) -> LLMClient:
    llm = types.SimpleNamespace(complete_structured=lambda *a: raw)
    return LLMClient(llm, types.SimpleNamespace(log=lambda *a: None))


def _candidate(entry_id: str) -> BufferedUtterance:
    return BufferedUtterance(entry_id, Utterance("open firefox", b"", 1.0), 0.0, dropped=True)
