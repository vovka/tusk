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
    "Classify transcribed speech into exactly one category:\n"
    "- command: a desktop action or tool invocation (e.g. 'open Firefox', 'close this window')\n"
    "- conversation: user talking TO TUSK but not a desktop action (e.g. 'what do you think?', 'explain how that works')\n"
    "- ambient: background noise, TV, other people, hallucination remnants\n"
    "Require wake word ('tusk'/'task') or obvious imperative/question for command or conversation. "
    'Respond ONLY with JSON: {"classification":"command"|"conversation"|"ambient",'
    '"cleaned_text":"<text without wake word>","reason":"<brief>"}.'
)

_FOLLOW_UP_ADDENDUM = (
    "\n\nIMPORTANT: The user recently interacted with TUSK. "
    "Recent conversation:\n{context}\n"
    "Contextual follow-ups (commands or conversational) should be classified "
    "as command or conversation, not ambient, even without a wake word. "
    "Only clearly unrelated ambient speech should be ambient. "
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
