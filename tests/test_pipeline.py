import types

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.pipeline import VoicePipeline
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.utterance import Utterance


def test_pipeline_submits_directed_text() -> None:
    queued, states = [], []
    result = list(_pipeline(GateDispatch("forward_current", "open Firefox"), states, _worker(queued)).run(_submitter([])))
    assert queued == ["open Firefox"] and states == [("forwarded", "u1")]
    assert result == []


def test_pipeline_drops_sanitized_phantoms() -> None:
    states = []
    pipeline = VoicePipeline(_detector("audio"), _transcriber("ghost"), _dropper(), _buffer(states), _gatekeeper(GateDispatch("forward_current", "open Firefox")), command_worker=_worker([]))
    assert list(pipeline.run(_submitter([]))) == []


def test_pipeline_drops_ambient_speech() -> None:
    pipeline = _pipeline(GateDispatch("drop"), [], _worker([]))
    assert list(pipeline.run(_submitter([]))) == []


def test_pipeline_submits_recovered_text_and_consumes_current_entry() -> None:
    queued, states = [], []
    dispatch = GateDispatch("forward_recovered", "open Firefox", "u0")
    list(_pipeline(dispatch, states, _worker(queued)).run(_submitter([])))
    assert queued == ["open Firefox"]
    assert states == [("recovered", "u0"), ("consumed", "u1")]


def test_pipeline_interrupts_and_consumes_current_entry() -> None:
    flushed, requested, states = [], [], []
    worker = _worker([], flushed)
    list(_pipeline(GateDispatch("interrupt"), states, worker, lambda: requested.append("stop")).run(_submitter([])))
    assert requested == ["stop"]
    assert flushed == ["flush"]
    assert states == [("consumed", "u1")]


def _pipeline(
    dispatch: GateDispatch, states: list[tuple[str, str]], worker: object, request_interrupt: object | None = None
) -> VoicePipeline:
    return VoicePipeline(
        _detector("audio"), _transcriber("open Firefox"), _sanitizer(), _buffer(states), _gatekeeper(dispatch),
        command_worker=worker, request_interrupt=request_interrupt,
    )


def _buffer(states: list[tuple[str, str]]) -> object:
    candidate = BufferedUtterance("u0", Utterance("open Firefox", b"", 1.0), 0.0, "dropped")
    return types.SimpleNamespace(process=_process, recent=lambda count: [], recoverable=lambda count, window: [candidate], mark_forwarded=lambda entry_id: states.append(("forwarded", entry_id)), mark_dropped=lambda entry_id: states.append(("dropped", entry_id)), mark_recovered=lambda entry_id: states.append(("recovered", entry_id)), mark_consumed=lambda entry_id: states.append(("consumed", entry_id)))


def _process(utterance: Utterance) -> BufferedUtterance:
    return BufferedUtterance("u1", utterance, 1.0)


def _detector(audio: str) -> object:
    utterance = Utterance("", audio.encode(), 1.0)
    return types.SimpleNamespace(stream_utterances=lambda: iter([utterance]))


def _dropper() -> object:
    return types.SimpleNamespace(process=lambda utterance: None)


def _gatekeeper(dispatch: GateDispatch) -> object:
    return types.SimpleNamespace(process=lambda utterance, recent, candidates=None: dispatch)


def _sanitizer() -> object:
    return types.SimpleNamespace(process=lambda utterance: utterance)


def _submitter(submits: list[str]) -> object:
    return lambda text: submits.append(text) or KernelResponse(True, "done")


def _transcriber(text: str) -> object:
    utterance = Utterance(text, b"audio", 1.0)
    return types.SimpleNamespace(process=lambda input_utterance: utterance)


def _worker(queued: list[str], flushed: list[str] | None = None) -> object:
    return types.SimpleNamespace(start=lambda submit: None, enqueue=queued.append, flush=lambda: _flush(flushed))


def _flush(flushed: list[str] | None) -> None:
    if flushed is not None:
        flushed.append("flush")
