from __future__ import annotations

from typing import TYPE_CHECKING

from tusk.core.agent import MainAgent
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
    'Respond ONLY with valid JSON: {"directed": true, "cleaned_command": "<text>"} '
    'or {"directed": false, "cleaned_command": ""}. '
    "For cleaned_command, strip any leading wake word ('tusk', 'task', 'hey tusk', 'hey task') "
    "and trim whitespace."
)


class CommandMode(PipelineMode):
    def __init__(self, agent: MainAgent, log_printer: LogPrinter) -> None:
        self._agent = agent
        self._log = log_printer

    @property
    def gatekeeper_prompt(self) -> str:
        return _GATEKEEPER_PROMPT

    def handle_utterance(self, gate_result: GateResult, utterance: Utterance, controller: PipelineController) -> None:
        if not gate_result.is_directed_at_tusk:
            self._log.log("GATE", "discarded")
            return
        self._log.log("GATE", f"command: {gate_result.cleaned_command!r}")
        self._agent.process_command(gate_result.cleaned_command)
