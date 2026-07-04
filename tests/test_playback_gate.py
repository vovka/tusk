import types

from shells.voice.gate_dispatch import GateDispatch
from shells.voice.playback_gate import PlaybackGate
from tusk.shared.schemas.utterance import Utterance


def test_playback_gate_interrupts_stop_intent_while_speaking() -> None:
    gate = PlaybackGate(_inner(), _llm("interrupt"), _log(), current_speech_text=lambda: "reply")
    assert gate.process(_utterance("forget it"), []).action == "interrupt"


def test_playback_gate_drops_echo_while_speaking() -> None:
    gate = PlaybackGate(_inner(), _llm("ambient"), _log(), current_speech_text=lambda: "reply")
    assert gate.process(_utterance("reply"), []).action == "drop"


def test_playback_gate_delegates_when_not_speaking() -> None:
    gate = PlaybackGate(_inner(), _llm("ambient"), _log(), current_speech_text=lambda: None)
    assert gate.process(_utterance("type hello"), []).text == "type hello"


def _inner() -> object:
    return types.SimpleNamespace(
        evaluate=lambda utterance, recent: None,
        process=lambda utterance, recent, candidates=None: GateDispatch("forward_current", utterance.text),
    )


def _llm(classification: str) -> object:
    payload = '{"classification":"' + classification + '","cleaned_text":"","reason":"test"}'
    return types.SimpleNamespace(label="gate", complete_structured=lambda *args: payload)


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
