import json

from tusk.kernel.dictation_gate_prompt import DICTATION_GATE_PROMPT
from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["DictationGate"]

_SCHEMA = {
    "type": "object",
    "properties": {
        "directed": {"type": "boolean"},
        "cleaned_command": {"type": "string"},
        "metadata_stop": {"type": ["string", "null"]},
    },
    "required": ["directed", "cleaned_command", "metadata_stop"],
    "additionalProperties": False,
}


class DictationGate:
    def __init__(self, llm: LLMProvider, log_printer: LogPrinter | None = None) -> None:
        self._llm = llm
        self._log = log_printer

    def should_stop(self, text: str) -> bool:
        data = self._parsed(self._complete(text))
        self._log_result(data)
        return bool(data.get("directed")) and _has_stop_reason(data.get("metadata_stop"))

    def _complete(self, text: str) -> str:
        try:
            return self._llm.complete_structured(DICTATION_GATE_PROMPT, text, "dictation_gatekeeper", _SCHEMA, 128)
        except Exception as exc:
            self._log_error("structured output failed", exc)
        try:
            return self._llm.complete(DICTATION_GATE_PROMPT, text, 128)
        except Exception as exc:
            self._log_error("fallback completion failed", exc)
            return ""

    def _parsed(self, raw: str) -> dict[str, object]:
        try:
            return _decoded(raw) if raw else {}
        except Exception as exc:
            self._log_error("parse error", exc)
            return {}

    def _log_error(self, message: str, exc: Exception) -> None:
        if self._log is not None:
            self._log.log("DICTATIONGATE", f"{message}: {exc}", "dictation-gate")

    def _log_result(self, data: dict[str, object]) -> None:
        if self._log is not None:
            self._log.log("DICTATIONGATE", f"directed={bool(data.get('directed'))} stop={data.get('metadata_stop')!r}", "dictation-gate")


def _decoded(raw: str) -> dict[str, object]:
    return _unwrap(json.loads(_extract_json(raw)))


def _extract_json(raw: str) -> str:
    text = raw.strip()
    return text.split("```")[1].lstrip("json").strip() if "```" in text else text


def _unwrap(data: dict | list) -> dict[str, object]:
    item = data[0] if isinstance(data, list) else data
    return item["arguments"] if "arguments" in item else item


def _has_stop_reason(value: object) -> bool:
    return value is not None and bool(str(value).strip())
