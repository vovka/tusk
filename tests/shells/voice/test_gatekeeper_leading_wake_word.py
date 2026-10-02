import types

from shells.voice.gate_action import GateAction
from shells.voice.stages.gate.gatekeeper import LLMGatekeeper
from tusk.shared.schemas.utterance import Utterance

_AMBIENT = '{"classification":"ambient","cleaned_text":"","reason":"misspelled wake word"}'


def _structured_failure(*_args) -> str:
    raise RuntimeError("json_validate_failed")


def _gatekeeper(complete) -> LLMGatekeeper:
    llm = types.SimpleNamespace(label="gate", complete_structured=_structured_failure, complete=complete)
    return LLMGatekeeper(llm, types.SimpleNamespace(log=lambda *a: None), time_source=lambda: 0.0)


def test_leading_wake_word_forwards_even_when_llm_says_ambient() -> None:
    # E2E: 'TOSK maximize it.' hit a structured 400, fallback said ambient, command was dropped
    dispatch = _gatekeeper(lambda *a: _AMBIENT).process(Utterance("TOSK maximize it.", b"", 1.0), [])
    assert dispatch.action == GateAction.FORWARD_CURRENT
    assert dispatch.kind == "command"
    assert dispatch.text == "TOSK maximize it."


def test_leading_wake_word_forwards_when_gatekeeper_llm_fails_entirely() -> None:
    dispatch = _gatekeeper(_structured_failure).process(Utterance("Tusk, maximize it.", b"", 1.0), [])
    assert dispatch.action == GateAction.FORWARD_CURRENT


def test_mid_sentence_wake_word_still_respects_ambient() -> None:
    dispatch = _gatekeeper(lambda *a: _AMBIENT).process(Utterance("I told tusk about it.", b"", 1.0), [])
    assert dispatch.action == GateAction.DROP
