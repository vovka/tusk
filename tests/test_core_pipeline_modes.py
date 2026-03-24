from types import SimpleNamespace

from tusk.core.command_mode import CommandMode
from tusk.core.dictation_mode import DictationMode
from tusk.core.monotonic_interaction_clock import MonotonicInteractionClock
from tusk.core.pipeline import Pipeline
from tusk.core.utterance_detector import UtteranceDetector
from tusk.schemas.gate_result import GateResult
from tusk.schemas.utterance import Utterance


def test_clock_window(monkeypatch) -> None:
    vals = iter([10.0, 12.0, 20.0])
    monkeypatch.setattr("time.monotonic", lambda: next(vals))
    clock = MonotonicInteractionClock(5.0)
    clock.record_interaction()
    assert clock.is_within_follow_up_window()
    assert not clock.is_within_follow_up_window()


def test_command_mode_flow() -> None:
    agent = SimpleNamespace(process_command=lambda c: setattr(agent, "cmd", c))
    clock = SimpleNamespace(is_within_follow_up_window=lambda: False, record_interaction=lambda: setattr(clock, "hit", True))
    mode = CommandMode(agent, clock, SimpleNamespace(format_recent_context=lambda: ""), SimpleNamespace(log=lambda *a: None))
    mode.handle_utterance(GateResult(True, "open", 1.0), Utterance("", b"", 0.1), None)
    assert agent.cmd == "open" and clock.hit


def test_dictation_mode_dictates_and_stops() -> None:
    paster = SimpleNamespace(paste=lambda t: setattr(paster, "p", t), replace=lambda n, t: setattr(paster, "r", (n, t)))
    llm = SimpleNamespace(complete=lambda *a, **k: "Clean")
    mode = DictationMode(paster, llm, lambda: "command", SimpleNamespace(log=lambda *a: None))
    ctl = SimpleNamespace(set_mode=lambda m: setattr(ctl, "m", m))
    mode.handle_utterance(GateResult(False, "", 1.0), Utterance("hello", b"", 0.1), ctl)
    mode.handle_utterance(GateResult(True, "", 1.0, {"metadata_stop": "true"}), Utterance("", b"", 0.1), ctl)
    assert paster.r[1] == "Clean" and ctl.m == "command"


def test_pipeline_process_and_low_confidence() -> None:
    detector = SimpleNamespace(stream_utterances=lambda: iter([Utterance("a", b"1", 0.1)]))
    stt = SimpleNamespace(transcribe=lambda *a: Utterance("x", b"", 0.1, confidence=0.0))
    gate = SimpleNamespace(evaluate=lambda *a: GateResult(True, "x", 1.0))
    mode = SimpleNamespace(gatekeeper_prompt="g", handle_utterance=lambda *a: setattr(mode, "called", True))
    pipe = Pipeline(detector, stt, gate, mode, SimpleNamespace(audio_sample_rate=16000), SimpleNamespace(log=lambda *a: None))
    pipe.run()
    assert not hasattr(mode, "called")


def test_utterance_detector_yields() -> None:
    frames = [b"a"] * 5 + [b""] * 25
    detector = UtteranceDetector(SimpleNamespace(stream_frames=lambda: iter(frames)), 16000, 2, SimpleNamespace(log=lambda *a: None))
    items = list(detector.stream_utterances())
    assert len(items) == 1 and items[0].duration_seconds > 0
