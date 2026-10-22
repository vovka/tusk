from tusk.kernel.modes.coding_gate_prompt import CODING_GATE_PROMPT
from tusk.kernel.modes.dictation_gate_prompt import DICTATION_GATE_PROMPT
from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.llm.llm_json import extract_json_payload
from tusk.shared.llm.llm_registry import LLMRegistry
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["ModeGate"]

_PROMPTS = {"dictation": DICTATION_GATE_PROMPT, "coding": CODING_GATE_PROMPT}

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


class ModeGate:
    """Stop classifier for a forward-all mode: one instance per mode, prompt injected."""

    def __init__(self, llm: LLMProvider, mode_name: str, prompt: str, log_printer: LogPrinter | None = None) -> None:
        self._llm = llm
        self._prompt = prompt
        self._log = log_printer
        self._tag = f"{mode_name.upper()}GATE"
        self._group = f"{mode_name}-gate"
        self._schema_name = f"{mode_name}_gatekeeper"

    @classmethod
    def for_mode(cls, llm_registry: LLMRegistry | None, mode_name: str, log_printer: LogPrinter | None) -> "ModeGate":
        stop_gate_llm = llm_registry.get_with_fallback("stop_gate", "gatekeeper") if llm_registry else None
        return cls(stop_gate_llm, mode_name, _PROMPTS[mode_name], log_printer)

    def should_stop(self, text: str) -> bool:
        data = self._parsed(self._complete(text))
        self._log_result(data)
        return bool(data.get("directed")) and _has_stop_reason(data.get("metadata_stop"))

    def _complete(self, text: str) -> str:
        try:
            return self._llm.complete_structured(self._prompt, text, self._schema_name, _SCHEMA, 128)
        except Exception as exc:
            self._log_error("structured output failed", exc)
        try:
            return self._llm.complete(self._prompt, text, 128)
        except Exception as exc:
            self._log_error("fallback completion failed", exc)
            return ""

    def _parsed(self, raw: str) -> dict[str, object]:
        try:
            return extract_json_payload(raw) if raw else {}
        except ValueError as exc:
            self._log_error("parse error", exc)
            return {}

    def _log_error(self, message: str, exc: Exception) -> None:
        if self._log is not None:
            self._log.log("ERROR", f"{message}: {exc}", self._group)

    def _log_result(self, data: dict[str, object]) -> None:
        if self._log is not None:
            self._log.log(self._tag, f"directed={bool(data.get('directed'))} stop={data.get('metadata_stop')!r}", self._group)


def _has_stop_reason(value: object) -> bool:
    return value is not None and bool(str(value).strip())
