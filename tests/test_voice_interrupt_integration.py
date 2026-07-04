import threading
import types

from shells.voice.command_worker import CommandWorker
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.pipeline import VoicePipeline
from tusk.shared.interrupt import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.utterance import Utterance


def test_mock_voice_flow_interrupts_busy_worker_then_runs_next_command() -> None:
    token = InterruptToken()
    started, release = threading.Event(), threading.Event()
    submits: list[str] = []
    pipeline = _pipeline(CommandWorker(None, _playback(), _log(), token), token.interrupt, started)
    list(pipeline.run(_submitter(submits, started, release)))
    assert started.wait(timeout=1.0)
    assert token.is_interrupted is True
    release.set()
    assert _eventually(lambda: submits == ["slow task", "next task"])
    assert token.is_interrupted is False


def _pipeline(worker: CommandWorker, request_interrupt: object, started: threading.Event) -> VoicePipeline:
    dispatches = [GateDispatch("forward_current", "slow task"), GateDispatch("interrupt"), GateDispatch("forward_current", "next task")]
    return VoicePipeline(_detector(started), _same(), _same(), _buffer(), _gatekeeper(dispatches), command_worker=worker, request_interrupt=request_interrupt)


def _detector(started: threading.Event) -> object:
    def stream() -> object:
        yield Utterance("slow task", b"", 1.0)
        started.wait(timeout=1.0)
        yield Utterance("stop that", b"", 1.0)
        yield Utterance("next task", b"", 1.0)

    return types.SimpleNamespace(stream_utterances=stream)


def _same() -> object:
    return types.SimpleNamespace(process=lambda utterance: utterance)


def _buffer() -> object:
    ids = iter(["u1", "u2", "u3"])
    return types.SimpleNamespace(process=lambda utterance: _entry(next(ids), utterance), recent=lambda count: [], recoverable=lambda count, window: [], mark_forwarded=lambda entry_id: None, mark_dropped=lambda entry_id: None, mark_consumed=lambda entry_id: None)


def _entry(entry_id: str, utterance: Utterance) -> object:
    return types.SimpleNamespace(id=entry_id, text=utterance.text, utterance=utterance)


def _gatekeeper(dispatches: list[GateDispatch]) -> object:
    return types.SimpleNamespace(process=lambda utterance, recent, candidates=None: dispatches.pop(0))


def _submitter(submits: list[str], started: threading.Event, release: threading.Event) -> object:
    def submit(text: str) -> KernelResponse:
        submits.append(text)
        started.set()
        if text == "slow task":
            release.wait(timeout=1.0)
        return KernelResponse(True, "")

    return submit


def _eventually(condition: object) -> bool:
    pause = threading.Event()
    for _ in range(20):
        if condition():
            return True
        pause.wait(timeout=0.05)
    return False


def _playback() -> object:
    return types.SimpleNamespace(play=lambda wav: None)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
