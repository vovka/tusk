import types

from shells.voice.gate.llm_client import LLMClient
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.utterance import Utterance

_PAYLOAD = '{"classification": "command", "cleaned_text": "open firefox", "reason": "direct"}'


class _Log:
    def log(self, tag: str, message: str, group: str | None = None) -> None: ...


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


def test_string_arguments_payload_is_not_directed() -> None:
    result = _client('{"name": "command_gatekeeper", "arguments": "{}"}').primary("prompt", "text")
    assert not result.is_directed_at_tusk


def test_string_arguments_payload_recovers_nothing() -> None:
    decision = _client('{"name": "command_gate_recovery", "arguments": "{}"}').recovery("prompt", "text", [])
    assert decision.action == "none"


def test_fallback_completion_not_weaker_than_structured() -> None:
    fallback_calls: list[int] = []
    LLMClient(_llm(fallback_calls), _Log()).primary("prompt", "hello")
    assert fallback_calls == [1024]


def test_structured_budget_leaves_room_for_reasoning() -> None:
    # E2E: gpt-oss-20b spent all 512 tokens reasoning on "Tusk, yes." and returned no JSON, so the yes was lost
    budgets: list[int] = []

    def structured(prompt: str, text: str, name: str, schema: dict, max_tokens: int) -> str:
        budgets.append(max_tokens)
        return "{}"

    llm = types.SimpleNamespace(complete_structured=structured)
    LLMClient(llm, _Log()).primary("prompt", "hello")
    assert budgets == [1024]


def test_structured_only_client_skips_fallback_and_logs_to_its_group() -> None:
    fallback_calls: list[int] = []
    logs: list[tuple] = []
    log = types.SimpleNamespace(log=lambda *a: logs.append(a))
    client = LLMClient(_llm(fallback_calls), log, error_group="speech-stop", allow_fallback=False)
    assert client.complete("prompt", "hello", "speech_stop_gate", {}) == {}
    assert fallback_calls == []
    assert [entry[2] for entry in logs] == ["speech-stop"]


def test_structured_failure_is_logged_as_error() -> None:
    # E2E: a gatekeeper 400 json_validate_failed never surfaced as ERROR
    tags: list[str] = []
    log = types.SimpleNamespace(log=lambda tag, *a: tags.append(tag))
    LLMClient(_llm([]), log).primary("prompt", "hello")
    assert tags[0] == "ERROR"


def _client(raw: str) -> LLMClient:
    llm = types.SimpleNamespace(complete_structured=lambda *a: raw)
    return LLMClient(llm, types.SimpleNamespace(log=lambda *a: None))


def _candidate(entry_id: str) -> BufferedUtterance:
    return BufferedUtterance(entry_id, Utterance("open firefox", b"", 1.0), 0.0, dropped=True)


def _llm(fallback_calls: list[int]) -> object:
    def structured(*args: object) -> str:
        raise RuntimeError("empty completion from provider (finish_reason=length)")

    def complete(prompt: str, text: str, max_tokens: int) -> str:
        fallback_calls.append(max_tokens)
        return '{"classification":"ambient","cleaned_text":"","reason":"x"}'

    return types.SimpleNamespace(complete_structured=structured, complete=complete)
