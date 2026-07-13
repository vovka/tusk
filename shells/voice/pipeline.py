import queue
import threading
from collections.abc import Callable, Iterator

from shells.voice.gate_action import GateAction
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.gate_state import GateState
from shells.voice.interfaces.gatekeeper import Gatekeeper
from shells.voice.interfaces.transcription_buffer import TranscriptionBuffer
from shells.voice.stages.echo_filter import EchoFilter
from shells.voice.stages.sanitizer import Sanitizer
from shells.voice.stages.transcriber import Transcriber
from shells.voice.stages.utterance_detector import UtteranceDetector
from tusk.shared.status.interfaces.status_reporter import StatusReporter
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.utterance import Utterance

__all__ = ["VoicePipeline"]


class VoicePipeline:
    def __init__(
        self,
        detector: UtteranceDetector,
        transcriber: Transcriber,
        sanitizer: Sanitizer,
        buffer: TranscriptionBuffer,
        gatekeeper: Gatekeeper,
        recovery_window_seconds: float = 60.0,
        recovery_candidate_limit: int = 6,
        reporter: StatusReporter | None = None,
        on_interrupt: Callable[[], None] | None = None,
        echo_filter: EchoFilter | None = None,
    ) -> None:
        self._detector, self._transcriber = detector, transcriber
        self._sanitizer, self._buffer = sanitizer, buffer
        self._gatekeeper = gatekeeper
        self._recovery_window, self._recovery_limit = recovery_window_seconds, recovery_candidate_limit
        self._reporter, self._on_interrupt = reporter, on_interrupt
        self._echo_filter = echo_filter

    def run(self, submit: Callable[[str, str, str], KernelResponse | None]) -> Iterator[KernelResponse]:
        self._report(AppStatus.LISTENING)
        stop = threading.Event()
        utterances: queue.Queue[Utterance | Exception | None] = queue.Queue()
        threading.Thread(target=self._capture_into, args=(utterances, stop), daemon=True).start()
        try:
            yield from self._consume(utterances, submit)
        finally:
            stop.set()

    def _consume(
        self, utterances: "queue.Queue[Utterance | Exception | None]", submit: Callable[[str, str, str], KernelResponse | None],
    ) -> Iterator[KernelResponse]:
        while (item := utterances.get()) is not None:
            if isinstance(item, Exception):
                raise item
            result = self._handle_utterance(item, submit)
            if result is not None:
                yield result
            self._report(AppStatus.LISTENING)

    def _report(self, status: AppStatus, detail: str = "") -> None:
        if self._reporter is not None:
            self._reporter.set_status(status, detail)

    def _submit(self, text: str, refrain: str, kind: str, submit: Callable[[str, str, str], KernelResponse | None]) -> KernelResponse | None:
        self._report(AppStatus.REACTING, text)
        return submit(text, refrain, kind)

    def _capture_into(self, utterances: "queue.Queue[Utterance | Exception | None]", stop: threading.Event) -> None:
        # ponytail: capture+VAD stay real-time on this thread; STT and the agent run on
        # the consumer, so speech during an agent run is processed afterwards, not lost.
        try:
            for utterance in self._detector.stream_utterances():
                if stop.is_set():
                    return
                utterances.put(utterance)
            utterances.put(None)
        except Exception as exc:
            utterances.put(exc)

    def _handle_utterance(self, utterance: Utterance, submit: Callable[[str, str, str], KernelResponse | None]) -> KernelResponse | None:
        transcribed = self._transcriber.process(utterance)
        sanitized = self._sanitizer.process(transcribed)
        if sanitized is None or (self._echo_filter is not None and self._echo_filter.process(sanitized) is None):
            return None
        buffered = self._buffer.process(sanitized)
        if buffered is None:
            return None
        recent = self._buffer.recent(7)[:-1]
        candidates = self._buffer.recoverable(self._recovery_limit, self._recovery_window)
        return self._dispatch(self._gatekeeper.process(buffered, recent, candidates), buffered.id, submit)

    def _dispatch(self, result: GateDispatch, current_id: str, submit: Callable[[str, str, str], KernelResponse | None]) -> KernelResponse | None:
        if result.action == GateAction.INTERRUPT:
            return self._interrupt(current_id)
        if result.action == GateAction.DROP or result.text is None:
            self._buffer.mark(current_id, GateState.DROPPED)
            return None
        self._mark_accepted(result, current_id)
        return self._submit(result.text, result.intent, result.kind, submit)

    def _mark_accepted(self, result: GateDispatch, current_id: str) -> None:
        if result.action == GateAction.FORWARD_RECOVERED:
            self._buffer.mark(result.recovered_id, GateState.RECOVERED)
            self._buffer.mark(current_id, GateState.CONSUMED)
            return
        self._buffer.mark(current_id, GateState.FORWARDED)

    def _interrupt(self, current_id: str) -> None:
        self._buffer.mark(current_id, GateState.CONSUMED)
        if self._on_interrupt is not None:
            self._on_interrupt()
