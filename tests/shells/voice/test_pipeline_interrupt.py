import types

from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from shells.voice.pipeline import VoicePipeline
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.voice.utterance import Utterance


def test_interrupt_dispatch_fires_callback_and_forwards_nothing() -> None:
    interrupts: list[bool] = []
    dropped: list[str] = []
    submits: list[str] = []
    pipeline = _pipeline(GateDispatch("interrupt"), dropped, lambda: interrupts.append(True))
    results = list(pipeline.run(_submit(submits)))
    assert interrupts == [True]
    assert dropped == []  # an interrupt is consumed, never a recovery candidate
    assert submits == []
    assert results == []


def test_interrupt_dispatch_without_callback_is_safe() -> None:
    pipeline = _pipeline(GateDispatch("interrupt"), [], on_interrupt=None)
    assert list(pipeline.run(_submit([]))) == []


def _pipeline(dispatch: GateDispatch, dropped: list[str], on_interrupt) -> VoicePipeline:
    utterance = Utterance("stop it", b"audio", 1.0)
    return VoicePipeline(
        types.SimpleNamespace(stream_utterances=lambda: iter([utterance])),
        types.SimpleNamespace(process=lambda item: utterance),
        types.SimpleNamespace(process=lambda item: item),
        _buffer(dropped),
        types.SimpleNamespace(process=lambda item, recent, candidates: dispatch),
        on_interrupt=on_interrupt,
    )


def _buffer(dropped: list[str]) -> object:
    entry = BufferedUtterance("u1", Utterance("stop it", b"", 1.0), 1.0)
    return types.SimpleNamespace(
        process=lambda item: entry,
        recent=lambda count: [],
        recoverable=lambda count, window: [],
        mark_dropped=dropped.append,
    )


def _submit(submits: list[str]):
    def submit(text: str, refrain: str = "", kind: str = "conversation") -> KernelResponse:
        submits.append(text)
        return KernelResponse(True, "done")
    return submit
