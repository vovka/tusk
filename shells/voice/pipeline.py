import queue
import threading
from collections.abc import Callable, Iterator

from shells.voice.gate_dispatch import GateDispatch
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.utterance import Utterance

__all__ = ["VoicePipeline"]


class VoicePipeline:
    def __init__(
        self,
        detector: object,
        transcriber: object,
        sanitizer: object,
        buffer: object,
        gatekeeper: object,
        recovery_window_seconds: float = 60.0,
        recovery_candidate_limit: int = 6,
        reporter: object | None = None,
        on_interrupt: Callable[[], None] | None = None,
    ) -> None:
        self._detector = detector
        self._transcriber = transcriber
        self._sanitizer = sanitizer
        self._buffer = buffer
        self._gatekeeper = gatekeeper
        self._recovery_window = recovery_window_seconds
        self._recovery_limit = recovery_candidate_limit
        self._reporter = reporter
        self._on_interrupt = on_interrupt

    def run(self, submit: Callable[[str], KernelResponse]) -> Iterator[KernelResponse]:
        self._report(AppStatus.LISTENING)
        stop = threading.Event()
        utterances: queue.Queue[Utterance | Exception | None] = queue.Queue()
        threading.Thread(target=self._capture_into, args=(utterances, stop), daemon=True).start()
        try:
            yield from self._consume(utterances, submit)
        finally:
            stop.set()

    def _consume(
        self, utterances: "queue.Queue[Utterance | Exception | None]", submit: Callable[[str], KernelResponse],
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

    def _submit(self, text: str, submit: Callable[[str], KernelResponse]) -> KernelResponse:
        self._report(AppStatus.REACTING, text)
        return submit(text)

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

    def _handle_utterance(self, utterance: Utterance, submit: Callable[[str], KernelResponse]) -> KernelResponse | None:
        transcribed = self._transcriber.process(utterance)
        sanitized = self._sanitizer.process(transcribed)
        if sanitized is None:
            return None
        buffered = self._buffer.process(sanitized)
        if buffered is None:
            return None
        recent = self._buffer.recent(7)[:-1]
        candidates = self._buffer.recoverable(self._recovery_limit, self._recovery_window)
        return self._dispatch(self._gatekeeper.process(buffered, recent, candidates), buffered.id, submit)

    def _dispatch(self, result: GateDispatch, current_id: str, submit: Callable[[str], KernelResponse]) -> KernelResponse | None:
        if result.action == "interrupt":
            return self._interrupt(current_id)
        if result.action == "drop" or result.text is None:
            self._buffer.mark_dropped(current_id)
            return None
        self._mark_accepted(result, current_id)
        return self._submit(result.text, submit)

    def _mark_accepted(self, result: GateDispatch, current_id: str) -> None:
        if result.action == "forward_recovered":
            self._buffer.mark_recovered(result.recovered_id)
            self._buffer.mark_consumed(current_id)
            return
        self._buffer.mark_forwarded(current_id)

    def _interrupt(self, current_id: str) -> None:
        self._buffer.mark_consumed(current_id)
        if self._on_interrupt is not None:
            self._on_interrupt()
        return None
