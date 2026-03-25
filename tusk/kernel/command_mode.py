from tusk.kernel.interfaces.agent import Agent
from tusk.kernel.interfaces.interaction_clock import InteractionClock
from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.recent_context_formatter import RecentContextFormatter
from tusk.kernel.schemas.gate_result import GateResult
from tusk.kernel.schemas.kernel_response import KernelResponse

__all__ = ["CommandMode"]

_BASE_PROMPT = "\n".join([
    "You are the gatekeeper for a voice assistant named TUSK.",
    "Classify each utterance as command, conversation, or ambient.",
    "Treat direct wake-word requests as command.",
    "Treat obvious desktop commands as command even without a wake word.",
    "If the utterance is conversational but explicitly addresses TUSK, classify it as conversation.",
    "Treat background speech, filler, and unrelated chatter as ambient.",
    "Return strict JSON only: {\"classification\":\"command|conversation|ambient\",\"cleaned_text\":\"...\",\"reason\":\"...\"}.",
    "For command or conversation, remove wake words like 'tusk', 'task', 'hey tusk', or 'hey task'.",
])


class CommandMode:
    def __init__(
        self,
        agent: Agent,
        interaction_clock: InteractionClock,
        context_formatter: RecentContextFormatter,
        log_printer: LogPrinter,
    ) -> None:
        self._agent = agent
        self._clock = interaction_clock
        self._formatter = context_formatter
        self._log = log_printer

    @property
    def gatekeeper_prompt(self) -> str:
        if not self._clock.is_within_follow_up_window():
            return _BASE_PROMPT
        context = self._formatter.format_recent_context()
        if not context:
            return _BASE_PROMPT
        return "\n".join([
            _BASE_PROMPT,
            "The user recently interacted with TUSK. Follow-up utterances may omit the wake word.",
            "Recent context:",
            context,
        ])

    def handle_gate_result(self, gate_result: GateResult) -> KernelResponse:
        if not gate_result.is_directed_at_tusk:
            self._log.log("GATE", "discarded")
            return KernelResponse(False, "")
        return self.process_command(gate_result.cleaned_command)

    def process_command(self, command: str) -> KernelResponse:
        self._log.log("GATE", f"command: {command!r}")
        reply = self._agent.process_command(command)
        self._clock.record_interaction()
        return KernelResponse(True, reply)
