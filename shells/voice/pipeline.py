import queue
import threading
from collections.abc import Callable, Iterator

from shells.voice.pipeline_dispatcher import PipelineDispatcher
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
        command_worker: object | None = None,
        request_interrupt: Callable[[], None] | None = None,
    ) -> None:
        self._detector = detector
        self._transcriber = transcriber
        self._sanitizer = sanitizer
        self._buffer = buffer
        self._gatekeeper = gatekeeper
        self._recovery_window = recovery_window_seconds
        self._recovery_limit = recovery_candidate_limit
        self._reporter = reporter
        self._worker = command_worker
        self._dispatcher = PipelineDispatcher(buffer, command_worker, reporter, request_interrupt)

    def run(self, submit: Callable[[str], KernelResponse]) -> Iterator[KernelResponse]:
        self._report(AppStatus.LISTENING)
        self._worker.start(submit)
        stop = threading.Event()
        utterances: queue.Queue[Utterance | Exception | None] = queue.Queue()
        threading.Thread(target=self._capture_into, args=(utterances, stop), daemon=True).start()
        try:
            self._consume(utterances)
        finally:
            stop.set()
        return iter(())

    def _consume(
        self,
        utterances: "queue.Queue[Utterance | Exception | None]",
    ) -> None:
        while (item := utterances.get()) is not None:
            if isinstance(item, Exception):
                raise item
            self._handle_utterance(item)
            self._report(AppStatus.LISTENING)

    def _report(self, status: AppStatus, detail: str = "") -> None:
        if self._reporter is not None:
            self._reporter.set_status(status, detail)

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

    def _handle_utterance(
        self,
        utterance: Utterance,
    ) -> None:
        transcribed = self._transcriber.process(utterance)
        sanitized = self._sanitizer.process(transcribed)
        if sanitized is None:
            return None
        buffered = self._buffer.process(sanitized)
        if buffered is None:
            return None
        recent = self._buffer.recent(7)[:-1]
        candidates = self._buffer.recoverable(self._recovery_limit, self._recovery_window)
        self._dispatcher.dispatch(self._gatekeeper.process(buffered, recent, candidates), buffered.id)
