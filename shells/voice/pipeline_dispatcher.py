from collections.abc import Callable

from shells.voice.gate_dispatch import GateDispatch
from tusk.shared.schemas.app_status import AppStatus

__all__ = ["PipelineDispatcher"]


class PipelineDispatcher:
    def __init__(
        self, buffer: object, worker: object, reporter: object | None, request_interrupt: Callable[[], None] | None
    ) -> None:
        self._buffer = buffer
        self._worker = worker
        self._reporter = reporter
        self._request_interrupt = request_interrupt or (lambda: None)

    def dispatch(self, result: GateDispatch, current_id: str) -> None:
        if result.action == "interrupt":
            self._interrupt(current_id)
            return
        if result.action == "drop" or result.text is None:
            self._drop(current_id)
            return
        if result.action == "forward_recovered":
            self._recover(result, current_id)
            return
        self._forward(current_id, result.text)

    def _interrupt(self, current_id: str) -> None:
        self._request_interrupt()
        self._worker.flush()
        self._buffer.mark_consumed(current_id)

    def _drop(self, current_id: str) -> None:
        self._buffer.mark_dropped(current_id)

    def _recover(self, result: GateDispatch, current_id: str) -> None:
        self._buffer.mark_recovered(result.recovered_id)
        self._buffer.mark_consumed(current_id)
        self._enqueue(result.text or "")

    def _forward(self, current_id: str, text: str) -> None:
        self._buffer.mark_forwarded(current_id)
        self._enqueue(text)

    def _enqueue(self, text: str) -> None:
        if self._reporter is not None:
            self._reporter.set_status(AppStatus.REACTING, text)
        self._worker.enqueue(text)
