from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from tusk.interfaces.llm_provider import LLMProvider
from tusk.interfaces.log_printer import LogPrinter
from tusk.interfaces.pipeline_mode import PipelineMode
from tusk.interfaces.text_paster import TextPaster
from tusk.schemas.gate_result import GateResult
from tusk.schemas.utterance import Utterance

if TYPE_CHECKING:
    from tusk.interfaces.pipeline_controller import PipelineController

__all__ = ["DictationMode"]

_GATEKEEPER_PROMPT = (
    "You are monitoring dictation for a voice assistant named TUSK. "
    "Check ONLY if the user wants to STOP dictation. "
    "Stop signals: mentions of 'tusk'/'task' combined with 'stop'/'done'/'finish'/'end'. "
    "If stopping: "
    '{"directed": true, "cleaned_command": "", "metadata_stop": "true"}. '
    "If NOT stopping (normal dictation text): "
    '{"directed": false, "cleaned_command": "<the transcribed text verbatim>"}.'
)

_CLEANUP_PROMPT = (
    "Clean up this dictated text. Remove filler words (um, uh, oh, ah, like). "
    "Fix punctuation and capitalize sentences. Keep the meaning identical. "
    "Return ONLY the cleaned text, no explanation."
)


class DictationMode(PipelineMode):
    def __init__(
        self,
        text_paster: TextPaster,
        cleanup_llm: LLMProvider,
        command_mode_factory: Callable[[], PipelineMode],
        log_printer: LogPrinter,
    ) -> None:
        self._paster = text_paster
        self._cleanup_llm = cleanup_llm
        self._command_mode_factory = command_mode_factory
        self._log = log_printer
        self._raw_buffer: list[str] = []
        self._pasted_char_count: int = 0

    @property
    def gatekeeper_prompt(self) -> str:
        return _GATEKEEPER_PROMPT

    def handle_utterance(self, gate_result: GateResult, utterance: Utterance, controller: PipelineController) -> None:
        if gate_result.metadata.get("metadata_stop") == "true":
            self._handle_stop(controller)
            return
        self._handle_dictation(utterance.text)

    def _handle_dictation(self, text: str) -> None:
        if not text:
            return
        paste_text = f" {text}" if self._raw_buffer else text
        self._paster.paste(paste_text)
        self._pasted_char_count += len(paste_text)
        self._raw_buffer.append(text)

    def _handle_stop(self, controller: PipelineController) -> None:
        if self._raw_buffer:
            self._cleanup_and_replace()
        self._log.log("DICTATION", "stopped")
        controller.set_mode(self._command_mode_factory())

    def _cleanup_and_replace(self) -> None:
        raw_text = " ".join(self._raw_buffer)
        cleaned = self._cleanup_llm.complete(_CLEANUP_PROMPT, raw_text)
        self._paster.replace(self._pasted_char_count, cleaned)
        self._pasted_char_count = len(cleaned)
