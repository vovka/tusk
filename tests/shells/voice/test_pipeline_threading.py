import threading
import types

import pytest

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.pipeline import VoicePipeline
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.utterance import Utterance


def test_capture_keeps_running_while_submit_is_busy() -> None:
    drained = threading.Event()
    submits: list[str] = []
    pipeline = _pipeline(_eager_detector(drained))
    results = list(pipeline.run(_busy_submitter(drained, submits)))
    assert submits == ["open Firefox", "open Firefox"]
    assert len(results) == 2


def test_pipeline_propagates_capture_failures() -> None:
    pipeline = _pipeline(_failing_detector())
    with pytest.raises(RuntimeError, match="microphone unplugged"):
        list(pipeline.run(lambda text, refrain="": KernelResponse(True, "done")))


def test_capture_thread_stops_when_generator_is_closed() -> None:
    proceed = threading.Event()
    pipeline = _pipeline(_endless_detector(proceed))
    before = set(threading.enumerate())
    generator = pipeline.run(lambda text, refrain="": KernelResponse(True, "done"))
    next(generator)
    capture_thread = (set(threading.enumerate()) - before).pop()
    generator.close()
    proceed.set()
    capture_thread.join(timeout=2.0)
    assert not capture_thread.is_alive()


def _pipeline(detector: object) -> VoicePipeline:
    transcribed = Utterance("open Firefox", b"audio", 1.0)
    return VoicePipeline(
        detector,
        types.SimpleNamespace(process=lambda utterance: transcribed),
        types.SimpleNamespace(process=lambda utterance: utterance),
        _buffer(),
        types.SimpleNamespace(process=lambda utterance, recent, candidates=None: GateDispatch("forward_current", "open Firefox")),
    )


def _eager_detector(drained: threading.Event) -> object:
    def stream():
        yield Utterance("", b"one", 1.0)
        yield Utterance("", b"two", 1.0)
        drained.set()

    return types.SimpleNamespace(stream_utterances=stream)


def _failing_detector() -> object:
    def stream():
        yield Utterance("", b"one", 1.0)
        raise RuntimeError("microphone unplugged")

    return types.SimpleNamespace(stream_utterances=stream)


def _endless_detector(proceed: threading.Event) -> object:
    def stream():
        while True:
            yield Utterance("", b"x", 1.0)
            proceed.wait(timeout=5.0)

    return types.SimpleNamespace(stream_utterances=stream)


def _busy_submitter(drained: threading.Event, submits: list[str]) -> object:
    def submit(text: str, refrain: str = "") -> KernelResponse:
        assert drained.wait(timeout=5.0), "capture stalled while the agent was busy"
        submits.append(text)
        return KernelResponse(True, "done")

    return submit


def _buffer() -> object:
    entries = iter([BufferedUtterance("u1", Utterance("open Firefox", b"", 1.0), 1.0), BufferedUtterance("u2", Utterance("open Firefox", b"", 1.0), 2.0)])
    return types.SimpleNamespace(process=lambda utterance: next(entries), recent=lambda count: [], recoverable=lambda count, window: [], mark=lambda entry_id, state: None)
