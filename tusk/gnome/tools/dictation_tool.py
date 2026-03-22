from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from tusk.core.dictation_mode import DictationMode
from tusk.interfaces.agent_tool import AgentTool
from tusk.interfaces.llm_provider import LLMProvider
from tusk.interfaces.pipeline_mode import PipelineMode
from tusk.interfaces.text_paster import TextPaster
from tusk.schemas.tool_result import ToolResult

if TYPE_CHECKING:
    from tusk.interfaces.pipeline_controller import PipelineController

__all__ = ["DictationTool"]


class DictationTool(AgentTool):
    def __init__(
        self,
        pipeline_controller: PipelineController,
        text_paster: TextPaster,
        cleanup_llm: LLMProvider,
        command_mode_factory: Callable[[], PipelineMode],
    ) -> None:
        self._controller = pipeline_controller
        self._text_paster = text_paster
        self._cleanup_llm = cleanup_llm
        self._command_mode_factory = command_mode_factory

    @property
    def name(self) -> str:
        return "start_dictation"

    @property
    def description(self) -> str:
        return "Start dictation mode to capture and paste spoken text"

    @property
    def parameters_schema(self) -> dict[str, str]:
        return {}

    def execute(self, parameters: dict[str, str]) -> ToolResult:
        mode = DictationMode(
            text_paster=self._text_paster,
            cleanup_llm=self._cleanup_llm,
            command_mode_factory=self._command_mode_factory,
        )
        self._controller.set_mode(mode)
        return ToolResult(success=True, message="dictation mode started")
