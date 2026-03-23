from __future__ import annotations

from typing import TYPE_CHECKING

from tusk.core.agent import MainAgent
from tusk.core.recent_context_formatter import RecentContextFormatter
from tusk.interfaces.interaction_clock import InteractionClock
from tusk.interfaces.log_printer import LogPrinter
from tusk.interfaces.pipeline_mode import PipelineMode
from tusk.schemas.gate_result import GateResult
from tusk.schemas.utterance import Utterance

if TYPE_CHECKING:
    from tusk.interfaces.pipeline_controller import PipelineController

__all__ = ["CommandMode"]

_GATEKEEPER_PROMPT = (
    "You are a gatekeeper for a voice assistant named TUSK. "
    "Decide if the transcribed speech is a command directed at TUSK. "
    "It is directed at TUSK if it mentions 'tusk' or 'task' (common mishearing) "
    "or is a clear imperative desktop command (e.g. 'open firefox', 'close this window'). "
    'Respond ONLY with valid JSON: {"directed": true, "cleaned_command": "<text>", "reason": "<brief explanation>"} '
    'or {"directed": false, "cleaned_command": "", "reason": "<brief explanation>"}. '
    "For cleaned_command, strip any leading wake word ('tusk', 'task', 'hey tusk', 'hey task') "
    "and trim whitespace."
)

_FOLLOW_UP_ADDENDUM = (
    "\n\nIMPORTANT: The user recently interacted with TUSK. "
    "Recent conversation:\n{context}\n"
    "If this new utterance is a contextual follow-up to the above conversation "
    "(e.g. 'and also...', 'now do...', 'what about...', 'close the other one', "
    "'do the same for...'), treat it as directed at TUSK even without a wake word. "
    "Still respond with the same JSON format."
)


class CommandMode(PipelineMode):
    def __init__(
        self,
        agent: MainAgent,
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
            return _GATEKEEPER_PROMPT
        return self._build_contextual_prompt()

    def _build_contextual_prompt(self) -> str:
        context = self._formatter.format_recent_context()
        if not context:
            return _GATEKEEPER_PROMPT
        return _GATEKEEPER_PROMPT + _FOLLOW_UP_ADDENDUM.format(context=context)

    def handle_utterance(
        self, gate_result: GateResult, utterance: Utterance, controller: PipelineController,
    ) -> None:
        if not gate_result.is_directed_at_tusk:
            self._log.log("GATE", "discarded")
            return
        self._log.log("GATE", f"command: {gate_result.cleaned_command!r}")
        self._agent.process_command(gate_result.cleaned_command)
        self._clock.record_interaction()
