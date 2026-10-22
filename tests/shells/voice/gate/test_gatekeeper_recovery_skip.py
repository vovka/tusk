import types

from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate.llm_gatekeeper import LLMGatekeeper
from tusk.shared.schemas.voice.utterance import Utterance


def test_recovery_is_skipped_for_non_referential_ambient_chatter() -> None:
    calls = _gatekeeper([_ambient()]).process(_buffered("the weather is lovely today"), [], _candidates())
    assert calls.action == "drop"
    assert _CALL_COUNT["n"] == 1  # only the primary classification, no recovery call


def test_recovery_runs_when_utterance_has_a_reference_cue() -> None:
    _gatekeeper([_ambient(), _none()]).process(_buffered("no the last one"), [], _candidates())
    assert _CALL_COUNT["n"] == 2


def test_recovery_runs_for_directed_conversation_without_a_cue() -> None:
    _gatekeeper([_conversation(), _none()]).process(_buffered("good morning friend"), [], _candidates())
    assert _CALL_COUNT["n"] == 2


def test_recovery_runs_when_wake_word_present() -> None:
    _gatekeeper([_ambient(), _none()]).process(_buffered("hello there tusk"), [], _candidates())
    assert _CALL_COUNT["n"] == 2


_CALL_COUNT = {"n": 0}


def _gatekeeper(responses: list[str]) -> LLMGatekeeper:
    _CALL_COUNT["n"] = 0

    def complete_structured(prompt: str, *_args) -> str:
        _CALL_COUNT["n"] += 1
        return responses.pop(0)

    llm = types.SimpleNamespace(label="gate", complete_structured=complete_structured)
    return LLMGatekeeper(llm, types.SimpleNamespace(log=lambda *a: None), time_source=lambda: 0.0)


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _buffered(text: str) -> BufferedUtterance:
    return BufferedUtterance("u2", _utterance(text), 2.0)


def _candidates() -> list[BufferedUtterance]:
    return [BufferedUtterance("u1", _utterance("open Firefox"), 1.0, dropped=True)]


def _ambient() -> str:
    return '{"classification":"ambient","cleaned_text":"","reason":"noise"}'


def _conversation() -> str:
    return '{"classification":"conversation","cleaned_text":"good morning friend","reason":"chat"}'


def _none() -> str:
    return '{"action":"none","candidate_id":"","reason":"no link"}'
