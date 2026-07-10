import types

from shells.voice.gate_dispatch import GateDispatch
from shells.voice.playback_gate import PlaybackGate
from tusk.shared.schemas.utterance import Utterance


def test_delegates_to_inner_when_not_speaking() -> None:
    inner_calls: list[str] = []
    gate = _gate(inner_calls, speaking=None, stop=False)
    dispatch = gate.process(_utterance("type hello"), [])
    assert dispatch.action == "forward_current"
    assert inner_calls == ["type hello"]


def test_stop_intent_during_playback_interrupts() -> None:
    inner_calls: list[str] = []
    gate = _gate(inner_calls, speaking="reading a long reply", stop=True)
    dispatch = gate.process(_utterance("that's enough, be quiet"), [])
    assert dispatch.action == "interrupt"
    assert inner_calls == []


def test_non_stop_speech_during_playback_is_dropped() -> None:
    inner_calls: list[str] = []
    gate = _gate(inner_calls, speaking="reading a long reply", stop=False)
    dispatch = gate.process(_utterance("reading a long reply"), [])
    assert dispatch.action == "drop"
    assert inner_calls == []


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _gate(inner_calls: list[str], speaking: str | None, stop: bool) -> PlaybackGate:
    inner = types.SimpleNamespace(
        process=lambda utterance, recent, candidates=None: inner_calls.append(utterance.text) or GateDispatch("forward_current", utterance.text),
    )
    stop_gate = types.SimpleNamespace(should_stop=lambda text, speaking: stop)
    return PlaybackGate(inner, lambda: speaking, stop_gate)
