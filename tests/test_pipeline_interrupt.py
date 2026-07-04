import types

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.pipeline import VoicePipeline
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.utterance import Utterance


def test_interrupt_dispatch_fires_callback_and_forwards_nothing() -> None:
    interrupts: list[bool] = []
    consumed: list[str] = []
    submits: list[str] = []
    pipeline = _pipeline(GateDispatch("interrupt"), consumed, lambda: interrupts.append(True))
    results = list(pipeline.run(_submit(submits)))
    assert interrupts == [True]
    assert consumed == ["u1"]
    assert submits == []
    assert results == []


def test_interrupt_dispatch_without_callback_is_safe() -> None:
    consumed: list[str] = []
    pipeline = _pipeline(GateDispatch("interrupt"), consumed, on_interrupt=None)
    assert list(pipeline.run(_submit([]))) == []
    assert consumed == ["u1"]


def _pipeline(dispatch: GateDispatch, consumed: list[str], on_interrupt) -> VoicePipeline:
    utterance = Utterance("stop it", b"audio", 1.0)
    return VoicePipeline(
        types.SimpleNamespace(stream_utterances=lambda: iter([utterance])),
        types.SimpleNamespace(process=lambda item: utterance),
        types.SimpleNamespace(process=lambda item: item),
        _buffer(consumed),
        types.SimpleNamespace(process=lambda item, recent, candidates=None: dispatch),
        on_interrupt=on_interrupt,
    )


def _buffer(consumed: list[str]) -> object:
    entry = BufferedUtterance("u1", Utterance("stop it", b"", 1.0), 1.0)
    return types.SimpleNamespace(
        process=lambda item: entry,
        recent=lambda count: [],
        recoverable=lambda count, window: [],
        mark_consumed=lambda entry_id: consumed.append(entry_id),
        mark_forwarded=lambda entry_id: None,
        mark_dropped=lambda entry_id: None,
    )


def _submit(submits: list[str]):
    def submit(text: str) -> KernelResponse:
        submits.append(text)
        return KernelResponse(True, "done")
    return submit
