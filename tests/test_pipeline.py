import types

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.pipeline import VoicePipeline
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.utterance import Utterance


def test_pipeline_submits_directed_text() -> None:
    submits, states = [], []
    result = list(_pipeline(GateDispatch("forward_current", "open Firefox"), states).run(_submitter(submits)))
    assert submits == ["open Firefox"] and states == [("forwarded", "u1")]
    assert result == [KernelResponse(True, "done")]


def test_pipeline_drops_sanitized_phantoms() -> None:
    states = []
    pipeline = VoicePipeline(_detector("audio"), _transcriber("ghost"), _dropper(), _buffer(states), _gatekeeper(GateDispatch("forward_current", "open Firefox")))
    assert list(pipeline.run(_submitter([]))) == []


def test_pipeline_drops_ambient_speech() -> None:
    pipeline = _pipeline(GateDispatch("drop"), [])
    assert list(pipeline.run(_submitter([]))) == []


def test_pipeline_submits_recovered_text_and_consumes_current_entry() -> None:
    submits, states = [], []
    dispatch = GateDispatch("forward_recovered", "open Firefox", "u0")
    list(_pipeline(dispatch, states).run(_submitter(submits)))
    assert submits == ["open Firefox"]
    assert states == [("recovered", "u0"), ("consumed", "u1")]


def _pipeline(dispatch: GateDispatch, states: list[tuple[str, str]]) -> VoicePipeline:
    return VoicePipeline(_detector("audio"), _transcriber("open Firefox"), _sanitizer(), _buffer(states), _gatekeeper(dispatch))


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
