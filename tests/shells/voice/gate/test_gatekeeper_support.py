from shells.voice.gate.gatekeeper_support import fallback_dispatch, recent_context, recovered_dispatch
from shells.voice.gate.wake_words import has_wake_word, starts_with_wake_word
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_action import GateAction
from tusk.shared.schemas.voice.gate_classification import GateClassification
from tusk.shared.schemas.voice.gate_result import GateResult
from tusk.shared.schemas.voice.recovery_decision import RecoveryDecision
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


def test_recovered_dispatch_carries_command_kind() -> None:
    candidate = BufferedUtterance("c1", Utterance("open firefox", b"", 1.0), 0.0)
    dispatch = recovered_dispatch([candidate], RecoveryDecision("recover", candidate_id="c1"))
    assert dispatch.kind == "command"


def test_stt_mishearings_count_as_wake_word() -> None:
    assert has_wake_word("Tosk close it")
    assert has_wake_word("Dusk, open the browser")


def test_starts_with_wake_word_ignores_punctuation_and_case() -> None:
    assert starts_with_wake_word("TOSK, maximize it.")
    assert not starts_with_wake_word("I told tusk about it.")


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)
