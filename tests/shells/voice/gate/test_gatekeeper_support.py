from tusk.shared.schemas.voice.gate_action import GateAction
from shells.voice.gate.gatekeeper_support import PRIMARY_SCHEMA, fallback_dispatch, has_wake_word
from tusk.shared.schemas.voice.gate_classification import GateClassification
from tusk.shared.schemas.voice.gate_result import GateResult
from tusk.shared.schemas.voice.utterance import Utterance


def test_conversation_fallback_carries_intent() -> None:
    result = GateResult(True, "tell me a joke", 1.0, GateClassification.CONVERSATION, "Telling a joke")
    dispatch = fallback_dispatch(result, Utterance("tusk tell me a joke", b"", 1.0), True)
    assert dispatch.action == GateAction.FORWARD_CURRENT
    assert dispatch.intent == "Telling a joke"


def test_primary_schema_requires_intent() -> None:
    assert "intent" in PRIMARY_SCHEMA["properties"]
    assert "intent" in PRIMARY_SCHEMA["required"]


def test_tosk_mishearing_counts_as_wake_word() -> None:
    assert has_wake_word("Tosk close it")
