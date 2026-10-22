import types

from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from shells.voice.gate.playback_gate import PlaybackGate
from tusk.shared.schemas.voice.utterance import Utterance


def test_delegates_to_inner_when_not_speaking() -> None:
    inner_calls: list[str] = []
    gate = _gate(inner_calls, speaking=None, stop=False)
    dispatch = gate.process(_buffered("type hello"), [], [])
    assert dispatch.action == "forward_current"
    assert inner_calls == ["type hello"]


def test_stop_intent_during_playback_interrupts() -> None:
    inner_calls: list[str] = []
    gate = _gate(inner_calls, speaking="reading a long reply", stop=True)
    dispatch = gate.process(_buffered("that's enough, be quiet"), [], [])
    assert dispatch.action == "interrupt"
    assert inner_calls == []


def test_echo_of_spoken_fragment_during_playback_is_dropped() -> None:
    inner_calls: list[str] = []
    gate = _gate(inner_calls, speaking="Here is a short poem about the sea.", stop=False)
    dispatch = gate.process(_buffered("a short poem about the sea"), [], [])
    assert dispatch.action == "drop"
    assert inner_calls == []


def test_non_stop_command_during_playback_goes_to_inner_gatekeeper() -> None:
    # E2E: "TUSK Open the text editor." spoken over a reply got stop=False and was dropped
    inner_calls: list[str] = []
    gate = _gate(inner_calls, speaking="Switched the main agent.", stop=False)
    dispatch = gate.process(_buffered("TUSK Open the text editor."), [], [])
    assert dispatch.action == "forward_current"
    assert inner_calls == ["TUSK Open the text editor."]


def _buffered(text: str) -> BufferedUtterance:
    return BufferedUtterance("u1", Utterance(text, b"", 1.0), 1.0)


def _gate(inner_calls: list[str], speaking: str | None, stop: bool) -> PlaybackGate:
    inner = types.SimpleNamespace(
        process=lambda utterance, recent, candidates: inner_calls.append(utterance.text) or GateDispatch("forward_current", utterance.text),
    )
    stop_gate = types.SimpleNamespace(should_stop=lambda text, speaking: stop)
    return PlaybackGate(inner, lambda: speaking, stop_gate)
