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


def test_playback_gate_uses_fallback_completion_for_interrupt() -> None:
    gate = PlaybackGate(_inner(), _fallback_llm("interrupt"), _log(), current_speech_text=lambda: "reply")
    assert gate.process(_utterance("stop"), []).action == "interrupt"


def test_playback_gate_drops_parse_failure_and_logs_error() -> None:
    entries: list[tuple[str, str]] = []
    gate = PlaybackGate(_inner(), _raw_llm("not json"), _log(entries), current_speech_text=lambda: "reply")
    assert gate.process(_utterance("stop"), []).action == "drop"
    assert any(tag == "ERROR" for tag, message in entries)


def _inner() -> object:
    return types.SimpleNamespace(
        evaluate=lambda utterance, recent: None,
        process=lambda utterance, recent, candidates=None: GateDispatch("forward_current", utterance.text),
    )


def _llm(classification: str) -> object:
    payload = '{"classification":"' + classification + '","cleaned_text":"","reason":"test"}'
    return types.SimpleNamespace(label="gate", complete_structured=lambda *args: payload)


def _fallback_llm(classification: str) -> object:
    payload = '{"classification":"' + classification + '","cleaned_text":"","reason":"test"}'
    return types.SimpleNamespace(label="gate", complete_structured=_raise, complete=lambda *args: payload)


def _raw_llm(response: str) -> object:
    return types.SimpleNamespace(label="gate", complete_structured=lambda *args: response)


def _raise(*args: object) -> str:
    raise RuntimeError("structured failed")


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _log(entries: list[tuple[str, str]] | None = None) -> object:
    return types.SimpleNamespace(log=lambda tag, message, *args: _capture(entries, tag, message))


def _capture(entries: list[tuple[str, str]] | None, tag: str, message: str) -> None:
    if entries is not None:
        entries.append((tag, message))
