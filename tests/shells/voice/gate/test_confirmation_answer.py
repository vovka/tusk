import types

import pytest

from shells.voice.gate.confirmation_answer_gate import ConfirmationAnswerGate
from tusk.shared.schemas.voice.gate_action import GateAction
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from shells.voice.speech.confirmation_reply import ConfirmationReply
from shells.voice.stages.sanitizer import Sanitizer
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.utterance import Utterance

_QUESTION = [("Close window 'Notes - gedit'?", 99.0), ("Say 'Tusk, yes' to confirm.", 100.0)]
_AMBIENT = GateDispatch(GateAction.DROP)


def _reply(spoken: list[tuple[str, float]] = _QUESTION, now: float = 105.0) -> ConfirmationReply:
    return ConfirmationReply(lambda: spoken, now=lambda: now)


def _buffered(text: str) -> BufferedUtterance:
    return BufferedUtterance("u1", Utterance(text, b"", 1.0), 1.0)


def _gate(reply: ConfirmationReply) -> ConfirmationAnswerGate:
    return ConfirmationAnswerGate(types.SimpleNamespace(process=lambda utterance, recent, candidates: _AMBIENT), reply)


@pytest.mark.parametrize("heard", ["task yes", "Tusk, yes.", "dusk yeah", "TSK confirm!", "tusks do it", "Yes"])
def test_pending_confirmation_accepts_yes_without_gatekeeper(heard: str) -> None:
    dispatch = _gate(_reply()).process(_buffered(heard), [], [])
    assert dispatch == GateDispatch(GateAction.FORWARD_CURRENT, "yes", kind="command")


@pytest.mark.parametrize("heard", ["no", "Task, cancel."])
def test_pending_confirmation_accepts_no(heard: str) -> None:
    assert _gate(_reply()).process(_buffered(heard), [], []).text == "no"


def test_without_pending_confirmation_gatekeeper_decides() -> None:
    assert _gate(_reply(now=200.0)).process(_buffered("task yes"), [], []) == _AMBIENT
    assert _gate(_reply([("Done.", 100.0)])).process(_buffered("yes"), [], []) == _AMBIENT


def test_sanitizer_keeps_bare_yes_only_while_confirmation_pending() -> None:
    utterance = Utterance("Yes.", b"", 0.3)
    assert Sanitizer(confirmation_reply=_reply()).process(utterance) == utterance
    assert Sanitizer(confirmation_reply=_reply(now=200.0)).process(utterance) is None
