import json

from tusk.kernel.interfaces.gatekeeper import Gatekeeper
from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.schemas.gate_result import GateResult
from tusk.kernel.schemas.utterance import Utterance

__all__ = ["LLMGatekeeper"]

_COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "classification": {"type": "string", "enum": ["command", "conversation", "ambient"]},
        "cleaned_text": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["classification", "cleaned_text", "reason"],
    "additionalProperties": False,
}
_DICTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "directed": {"type": "boolean"},
        "cleaned_command": {"type": "string"},
        "metadata_stop": {"type": ["string", "null"]},
    },
    "required": ["directed", "cleaned_command", "metadata_stop"],
    "additionalProperties": False,
}


class LLMGatekeeper(Gatekeeper):
    def __init__(self, llm_provider: LLMProvider, log_printer: LogPrinter) -> None:
        self._llm = llm_provider
        self._log = log_printer

    def evaluate(self, utterance: Utterance, system_prompt: str) -> GateResult:
        schema_name, schema = _schema_for_prompt(system_prompt)
        raw = self._complete_with_fallback(system_prompt, utterance.text, schema_name, schema)
        if not raw:
            return GateResult(False, "", 0.0)
        self._log.log("LLM", f"[{self._llm.label}] gate → {raw!r}")
        try:
            data = _unwrap(json.loads(_extract_json(raw)))
            return _build_gate_result(data, self._log)
        except Exception as exc:
            self._log.log("GATE", f"parse error: {exc}")
            return GateResult(False, "", 0.0)

    def _complete_with_fallback(
        self,
        system_prompt: str,
        user_message: str,
        schema_name: str,
        schema: dict,
    ) -> str:
        try:
            return self._llm.complete_structured(system_prompt, user_message, schema_name, schema, 512)
        except Exception as exc:
            self._log.log("GATE", f"structured output failed: {exc}")
        try:
            return self._llm.complete(system_prompt, user_message, 256)
        except Exception as exc:
            self._log.log("GATE", f"fallback completion failed: {exc}")
            return ""


def _extract_json(raw: str) -> str:
    text = raw.strip()
    if "```" in text:
        text = text.split("```")[1].lstrip("json").strip()
    return text


def _unwrap(data: dict | list) -> dict:
    if isinstance(data, list):
        data = data[0]
    return data["arguments"] if "arguments" in data else data


def _build_gate_result(data: dict, log: LogPrinter) -> GateResult:
    reason = str(data.get("reason", ""))
    if reason:
        log.log("GATE", reason)
    classification = str(data.get("classification", "command" if data.get("directed") else "ambient"))
    cleaned = str(data.get("cleaned_text", data.get("cleaned_command", "")))
    metadata = {k: str(v) for k, v in data.items() if k.startswith("metadata_")}
    metadata["classification"] = classification
    return GateResult(classification in ("command", "conversation"), cleaned, 1.0, metadata)


def _schema_for_prompt(system_prompt: str) -> tuple[str, dict]:
    return ("dictation_gatekeeper", _DICTATION_SCHEMA) if "metadata_stop" in system_prompt else ("command_gatekeeper", _COMMAND_SCHEMA)
