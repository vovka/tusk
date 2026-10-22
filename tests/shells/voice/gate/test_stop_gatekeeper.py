import types

from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from shells.voice.gate.stop_gatekeeper import StopGatekeeper
from tusk.shared.schemas.voice.utterance import Utterance


def _utterance(text: str) -> Utterance:
    return Utterance(text=text, audio_frames=b"", duration_seconds=0.1)


def _buffered(text: str) -> BufferedUtterance:
    return BufferedUtterance(id="x", utterance=_utterance(text), received_at=0.0)


def _gate(stops: bool) -> object:
    return types.SimpleNamespace(should_stop=lambda text: stops)


def test_forwards_non_stop_utterance() -> None:
    gk = StopGatekeeper(_gate(False), lambda: None)
    result = gk.process(_utterance("hello world"), [])
    assert result == GateDispatch("forward_current", "hello world")


def test_forwards_buffered_non_stop_utterance() -> None:
    gk = StopGatekeeper(_gate(False), lambda: None)
    result = gk.process(_buffered("type this"), [])
    assert result == GateDispatch("forward_current", "type this")


def test_drops_stop_utterance() -> None:
    gk = StopGatekeeper(_gate(True), lambda: None)
    result = gk.process(_utterance("stop dictation"), [])
    assert result == GateDispatch("drop")


def test_calls_stop_callback_on_stop() -> None:
    called = []
    gk = StopGatekeeper(_gate(True), lambda: called.append(1))
    gk.process(_utterance("stop"), [])
    assert called == [1]


def test_does_not_call_stop_callback_for_normal_text() -> None:
    called = []
    gk = StopGatekeeper(_gate(False), lambda: called.append(1))
    gk.process(_utterance("just some text"), [])
    assert called == []


# Regression: in pair-coding mode "Tusk, stop pair coding mode." was typed into the editor as code.
def test_wake_word_stop_phrase_ends_the_mode_without_the_llm_gate() -> None:
    for text in ["Tusk, stop pair coding mode.", "Task, exit pair coating mode", "Dusk, done coding.",
                 "Tusk, stop dictation.", "Tusk stop coding"]:
        called = []
        gk = StopGatekeeper(_unused_gate(), lambda: called.append(1), _command_gate())
        assert gk.process(_utterance(text), []) == GateDispatch("drop") and called == [1], text


# Regression: "Tusk, use GPT OSS 120B for the main agent" was turned into code instead of switching the model.
def test_other_wake_word_utterance_goes_to_the_command_gatekeeper_bypassing_the_mode() -> None:
    gk = StopGatekeeper(_unused_gate(), lambda: None, _command_gate())
    result = gk.process(_utterance("Tusk, use GPT OSS 120B for the main agent."), [])
    assert result == GateDispatch("forward_current", "use GPT OSS 120B for the main agent", kind="mode-bypass:command")


def test_dropped_wake_word_utterance_stays_dropped() -> None:
    gk = StopGatekeeper(_unused_gate(), lambda: None, _command_gate(GateDispatch("drop")))
    assert gk.process(_utterance("Tusk is a nice name"), []) == GateDispatch("drop")


def test_utterance_without_wake_word_stays_a_mode_instruction() -> None:
    gk = StopGatekeeper(_gate(False), lambda: None, _command_gate())
    result = gk.process(_utterance("stop the loop after ten iterations"), [])
    assert result == GateDispatch("forward_current", "stop the loop after ten iterations")


def _unused_gate() -> object:
    return types.SimpleNamespace(should_stop=lambda text: (_ for _ in ()).throw(AssertionError("LLM gate called")))


def _command_gate(result: GateDispatch | None = None) -> object:
    dispatch = result or GateDispatch("forward_current", "use GPT OSS 120B for the main agent", kind="command")
    return types.SimpleNamespace(process=lambda utterance, recent, candidates=None: dispatch)


def _unused_gate() -> object:
    def fail(text: str) -> bool:
        raise AssertionError("LLM gate must not be called")
    return types.SimpleNamespace(should_stop=fail)


def test_bare_stop_phrase_stops_without_llm_gate() -> None:
    called = []
    gk = StopGatekeeper(_unused_gate(), lambda: called.append(1))
    assert gk.process(_utterance("Stop Pair Coating Mode."), []) == GateDispatch("drop")
    assert called == [1]


def test_stop_word_inside_dictated_text_still_forwards() -> None:
    gk = StopGatekeeper(_gate(False), lambda: None)
    result = gk.process(_utterance("stop the loop after ten iterations"), [])
    assert result.action == "forward_current"


def test_stt_variants_of_the_stop_phrase_stop_without_llm_gate() -> None:
    for text in ["Stop pair-coding mode.", "Stop pair-coating mode", "Stop paired coding mode.", "Stop pear coding mode",
                 "Stop pair programming.", "Okay, stop pair coding mode", "Stop pair coding mode please.", "Stop coding now"]:
        called = []
        gk = StopGatekeeper(_unused_gate(), lambda: called.append(1))
        assert gk.process(_utterance(text), []) == GateDispatch("drop") and called == [1], text
