import json
import time

from shells.voice.interfaces.gatekeeper import Gatekeeper
from shells.voice.stages.command_gate_prompt import build_command_gate_prompt
from shells.voice.stages.recent_context_formatter import RecentContextFormatter
from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.gate_result import GateResult
from tusk.shared.schemas.utterance import Utterance

__all__ = ["LLMGatekeeper"]

_SCHEMA = {
    "type": "object",
    "properties": {
        "classification": {"type": "string", "enum": ["command", "conversation", "ambient"]},
        "cleaned_text": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["classification", "cleaned_text", "reason"],
    "additionalProperties": False,
}


class LLMGatekeeper(Gatekeeper):
    def __init__(
        self,
        llm_provider: LLMProvider,
        log_printer: LogPrinter,
        formatter: RecentContextFormatter | None = None,
        time_source: object = time.monotonic,
        follow_up_window_seconds: float = 30.0,
    ) -> None:
        self._llm = llm_provider
        self._log = log_printer
        self._formatter = formatter or RecentContextFormatter()
        self._time = time_source
        self._window = follow_up_window_seconds
        self._last_forwarded_at: float | None = None

    def evaluate(self, utterance: Utterance, recent: list[Utterance]) -> GateResult:
        prompt = build_command_gate_prompt(self._context(recent))
        raw = self._complete(prompt, utterance.text)
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> GateResult:
        if not raw:
            return GateResult(False, "", 0.0)
        try:
            result, reason = _build_result(_unwrap(json.loads(_extract_json(raw))))
            self._log_result(result, reason)
            return result
        except Exception as exc:
            self._log.log("GATEKEEPER", f"parse error: {exc}", "gatekeeper")
            return GateResult(False, "", 0.0)

    def process(self, utterance: Utterance, recent: list[Utterance]) -> str | None:
        result = self.evaluate(utterance, recent)
        if not result.is_directed_at_tusk:
            return None
        self._last_forwarded_at = self._time()
        return result.cleaned_command

    def _complete(self, prompt: str, text: str) -> str:
        try:
            return self._llm.complete_structured(prompt, text, "command_gatekeeper", _SCHEMA, 512)
        except Exception as exc:
            self._log.log("GATEKEEPER", f"structured output failed: {exc}", "gatekeeper")
        try:
            return self._llm.complete(prompt, text, 256)
        except Exception as exc:
            self._log.log("GATEKEEPER", f"fallback completion failed: {exc}", "gatekeeper")
            return ""

    def _context(self, recent: list[Utterance]) -> str:
        if not self._within_follow_up_window():
            return ""
        return self._formatter.format(recent)

    def _within_follow_up_window(self) -> bool:
        if self._last_forwarded_at is None:
            return False
        return self._time() - self._last_forwarded_at <= self._window

    def _log_result(self, result: GateResult, reason: str) -> None:
        details = result.metadata.get("classification", "ambient")
        message = f"classification={details} directed={result.is_directed_at_tusk} text={result.cleaned_command!r}"
        self._log.log("GATEKEEPER", f"{message} reason={reason!r}", "gatekeeper")


def _extract_json(raw: str) -> str:
    text = raw.strip()
    if "```" in text:
        text = text.split("```")[1].lstrip("json").strip()
    return text


def _unwrap(data: dict | list) -> dict:
    item = data[0] if isinstance(data, list) else data
    return item["arguments"] if "arguments" in item else item


def _build_result(data: dict) -> tuple[GateResult, str]:
    reason = str(data.get("reason", ""))
    classification = str(data.get("classification", "ambient"))
    cleaned = str(data.get("cleaned_text", ""))
    result = GateResult(classification in ("command", "conversation"), cleaned, 1.0, {"classification": classification})
    return result, reason
