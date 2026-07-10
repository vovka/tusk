import threading
import uuid
from collections.abc import Callable

from tusk.kernel.modes.coding_gate_prompt import CODING_GATE_PROMPT
from tusk.kernel.modes.dictation_gate_prompt import DICTATION_GATE_PROMPT
from tusk.kernel.modes.mode_gate import ModeGate
from tusk.kernel.modes.mode_slot import ModeSlot
from tusk.kernel.core.submit_status_reporter import SubmitStatusReporter
from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.interrupt.interrupt_token import InterruptToken
from tusk.shared.llm.llm_registry import LLMRegistry
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.status.interfaces.status_reporter import StatusReporter
from tusk.shared.tracing.interfaces.tracer import Tracer
from tusk.shared.tracing.null_tracer import NullTracer

__all__ = ["KernelAPI"]

_TEXT_PREVIEW_CHARS = 240


class KernelAPI:
    def __init__(
        self, command_mode: object, llm_registry: LLMRegistry | None, log: LogPrinter | None = None,
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
        self._submit_reporter = SubmitStatusReporter(reporter) if reporter is not None else None
        self._submit_lock = threading.Lock()
        self._dictation = dictation_slot or ModeSlot("DICTATION", "Dictation started.")
        self._coding = coding_slot or ModeSlot("CODING", "Coding started.")

    def request_interrupt(self) -> None:
        if self._interrupt_token is not None:
            self._interrupt_token.interrupt()

    @property
    def interrupt_token(self) -> object | None:
        return self._interrupt_token

    def submit(self, text: str) -> KernelResponse:
        # ponytail: one global lock — commands are serial by design (single user voice stream)
        with self._submit_lock:
            self._log_input(text)
            attributes = {"request_id": uuid.uuid4().hex, "text_preview": text[:_TEXT_PREVIEW_CHARS]}
            with self._tracer.span("kernel.request", attributes):
                return self._reported_route(text)

    def _reported_route(self, text: str) -> KernelResponse:
        if self._submit_reporter is None:
            return self._route(text)
        return self._submit_reporter.run(text, self._route)

    def _log_input(self, text: str) -> None:
        if self._log is not None:
            self._log.log("KERNELINPUT", f"text={text!r}", "kernel-input")

    def _route(self, text: str) -> KernelResponse:
        if self._coding.active:
            return self._coding.process_text(text)
        if self._dictation.active:
            return self._dictation.process_text(text)
        return self._command_mode.process_command(text)

    def _report_mode(self, mode: AppMode) -> None:
        if self._reporter is not None:
            self._reporter.set_mode(mode)

    def set_dictation_callbacks(self, on_start: Callable[[], None], on_stop: Callable[[], None]) -> None:
        self._dictation.set_callbacks(on_start, on_stop)

    def request_dictation_stop(self) -> KernelResponse:
        return self._dictation.request_stop()

    def attach_dictation_router(self, router: object) -> None:
        self._dictation.attach_router(router)

    def start_dictation(self, state: object) -> KernelResponse:
        response = self._dictation.start(state, self._log)
        self._report_mode(AppMode.DICTATION)
        return response

    def stop_dictation(self) -> None:
        self._dictation.stop()
        self._report_mode(AppMode.DEFAULT)

    def set_coding_callbacks(self, on_start: Callable[[], None], on_stop: Callable[[], None]) -> None:
        self._coding.set_callbacks(on_start, on_stop)

    def request_coding_stop(self) -> KernelResponse:
        return self._coding.request_stop()

    def attach_coding_router(self, router: object) -> None:
        self._coding.attach_router(router)

    @property
    def coding_active(self) -> bool:
        return self._coding.active

    def start_coding(self, state: object) -> KernelResponse:
        return self._coding.start(state, self._log)

    def stop_coding(self) -> None:
        self._coding.stop()

    def get_llm_registry(self) -> LLMRegistry | None:
        return self._llm_registry

    def dictation_gate(self) -> ModeGate:
        return self._mode_gate("dictation", DICTATION_GATE_PROMPT)

    def coding_gate(self) -> ModeGate:
        return self._mode_gate("coding", CODING_GATE_PROMPT)

    def _mode_gate(self, mode_name: str, prompt: str) -> ModeGate:
        gatekeeper = self._llm_registry.get("gatekeeper") if self._llm_registry else None
        return ModeGate(gatekeeper, mode_name, prompt, self._log)
