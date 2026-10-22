import threading
import uuid

from tusk.kernel.core.command_mode import CommandMode
from tusk.kernel.modes.mode_slot import ModeSlot
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.interfaces.tracer import Tracer
from tusk.shared.interrupt_token import InterruptToken
from tusk.shared.llm.llm_registry import LLMRegistry
from tusk.shared.observability.null_tracer import NullTracer
from tusk.shared.observability.status_reporter import StatusReporter
from tusk.shared.schemas.app_mode import MODE_BYPASS_KIND_PREFIX, AppMode
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["KernelAPI"]

_TEXT_PREVIEW_CHARS = 240


class KernelAPI:
    def __init__(
        self, command_mode: CommandMode, llm_registry: LLMRegistry | None, log: LogPrinter | None = None,
        reporter: StatusReporter | None = None, interrupt_token: InterruptToken | None = None,
        dictation_slot: ModeSlot | None = None, coding_slot: ModeSlot | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._tracer = tracer or NullTracer()
        self._command_mode = command_mode
        self._llm_registry = llm_registry
        self._log = log
        self._reporter = reporter
        self._interrupt_token = interrupt_token
        self._submit_lock = threading.Lock()
        self._dictation = dictation_slot or ModeSlot(AppMode.DICTATION, "Dictation started.", log, reporter)
        self._coding = coding_slot or ModeSlot(AppMode.CODING, "Coding started.", log, reporter)

    def request_interrupt(self) -> None:
        if self._interrupt_token is not None:
            self._interrupt_token.interrupt()

    @property
    def interrupt_token(self) -> InterruptToken | None:
        return self._interrupt_token

    @property
    def llm_registry(self) -> LLMRegistry | None:
        return self._llm_registry

    @property
    def dictation(self) -> ModeSlot:
        return self._dictation

    @property
    def coding(self) -> ModeSlot:
        return self._coding

    def submit(self, text: str, kind: str = "conversation") -> KernelResponse:
        # ponytail: one global lock — commands are serial by design (single user voice stream)
        with self._submit_lock:
            self._log_input(text)
            attributes = {"request_id": uuid.uuid4().hex, "text_preview": text[:_TEXT_PREVIEW_CHARS]}
            with self._tracer.span("kernel.request", attributes) as span:
                response = self._reported_route(text, kind)
                span.set_attribute("handled", str(response.handled))
                return response

    def _reported_route(self, text: str, kind: str) -> KernelResponse:
        if self._reporter is None:
            return self._route(text, kind)
        previous = self._reporter.status
        self._reporter.set_status(AppStatus.REACTING, text)
        try:
            return self._route(text, kind)
        finally:
            self._reporter.set_status(previous)

    def _log_input(self, text: str) -> None:
        if self._log is not None:
            self._log.log("KERNELINPUT", f"text={text!r}", "kernel-input")

    def _route(self, text: str, kind: str) -> KernelResponse:
        # a wake-word command spoken during dictation/coding skips the mode
        if self._coding.active and not kind.startswith(MODE_BYPASS_KIND_PREFIX):
            return self._coding.process_text(text)
        if self._dictation.active and not kind.startswith(MODE_BYPASS_KIND_PREFIX):
            return self._dictation.process_text(text)
        return self._command_mode.process_command(text, kind.removeprefix(MODE_BYPASS_KIND_PREFIX))
