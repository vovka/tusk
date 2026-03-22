from __future__ import annotations

from typing import TYPE_CHECKING

from tusk.core.agent import MainAgent
from tusk.core.tool_registry import ToolRegistry
from tusk.interfaces.pipeline_mode import PipelineMode
from tusk.schemas.gate_result import GateResult

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
    def __init__(self, agent: MainAgent, tool_registry: ToolRegistry) -> None:
        self._agent = agent
        self._registry = tool_registry

    @property
    def gatekeeper_prompt(self) -> str:
        return _GATEKEEPER_PROMPT

    def handle_utterance(self, gate_result: GateResult, controller: PipelineController) -> None:
        if not gate_result.is_directed_at_tusk:
            print("[GATE] discarded")
            return
        print(f"[GATE] command: {gate_result.cleaned_command!r}")
        tool_call = self._agent.process_command(gate_result.cleaned_command)
        print(f"[AGENT] tool: {tool_call}")
        tool = self._registry.get(tool_call.tool_name)
        result = tool.execute(tool_call.parameters)
        print(f"[TOOL] {result.message}")
