from shells.voice.gate.gatekeeper_support import fallback_dispatch, recent_context
from tusk.shared.schemas.voice.gate_action import GateAction
from tusk.shared.schemas.voice.gate_classification import GateClassification
from tusk.shared.schemas.voice.gate_result import GateResult
from tusk.shared.schemas.voice.utterance import Utterance


def test_conversation_fallback_carries_intent() -> None:
    result = GateResult(True, "tell me a joke", 1.0, GateClassification.CONVERSATION, "Telling a joke")
    dispatch = fallback_dispatch(result, "tusk tell me a joke", True)
    assert dispatch.action == GateAction.FORWARD_CURRENT
    assert dispatch.intent == "Telling a joke"


def test_conversation_without_wake_word_is_dropped() -> None:
    result = GateResult(True, "tell me a joke", 1.0, GateClassification.CONVERSATION)
    assert fallback_dispatch(result, "tell me a joke", False).action == GateAction.DROP


def test_recent_context_skips_blank_lines_and_keeps_the_last_entries() -> None:
    utterances = [_utterance(text) for text in ("one", "  ", "two", "three")]
    assert recent_context(utterances, max_utterances=2) == "User: two\nUser: three"


def test_recent_context_truncates_long_utterances() -> None:
    assert recent_context([_utterance("x" * 200)]) == "User: " + "x" * 150


def test_recent_context_is_empty_without_utterances() -> None:
    assert recent_context([]) == ""


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)
