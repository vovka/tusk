import types

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.stages.dictation_gatekeeper import DictationGatekeeper
from tusk.shared.schemas.utterance import Utterance


def _utterance(text: str) -> Utterance:
    return Utterance(text=text, audio_frames=b"", duration_seconds=0.1)


def _buffered(text: str) -> BufferedUtterance:
    return BufferedUtterance(id="x", utterance=_utterance(text), received_at=0.0)


def _gate(stops: bool) -> object:
    return types.SimpleNamespace(should_stop=lambda text: stops)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)


def test_forwards_non_stop_utterance() -> None:
    gk = DictationGatekeeper(_gate(False), lambda: None, _log())
    result = gk.process(_utterance("hello world"), [])
    assert result == GateDispatch("forward_current", "hello world")


def test_forwards_buffered_non_stop_utterance() -> None:
    gk = DictationGatekeeper(_gate(False), lambda: None, _log())
    result = gk.process(_buffered("type this"), [])
    assert result == GateDispatch("forward_current", "type this")


def test_drops_stop_utterance() -> None:
    gk = DictationGatekeeper(_gate(True), lambda: None, _log())
    result = gk.process(_utterance("stop dictation"), [])
    assert result == GateDispatch("drop")


def test_calls_stop_callback_on_stop() -> None:
    called = []
    gk = DictationGatekeeper(_gate(True), lambda: called.append(1), _log())
    gk.process(_utterance("stop"), [])
    assert called == [1]


def test_does_not_call_stop_callback_for_normal_text() -> None:
    called = []
    gk = DictationGatekeeper(_gate(False), lambda: called.append(1), _log())
    gk.process(_utterance("just some text"), [])
    assert called == []
