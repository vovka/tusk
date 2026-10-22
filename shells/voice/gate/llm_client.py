from tusk.shared.interfaces.llm_provider import LLMProvider
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.llm.llm_json import extract_json_payload
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_classification import GateClassification
from tusk.shared.schemas.voice.gate_result import GateResult
from tusk.shared.schemas.voice.recovery_decision import RecoveryDecision

__all__ = ["LLMClient"]

_PRIMARY_SCHEMA = {
    "type": "object",
    "properties": {"classification": {"type": "string", "enum": ["command", "conversation", "ambient", "interrupt"]}, "cleaned_text": {"type": "string"}, "intent": {"type": "string"}, "reason": {"type": "string"}},
    "required": ["classification", "cleaned_text", "intent", "reason"],
    "additionalProperties": False,
}
_RECOVERY_SCHEMA = {
    "type": "object",
    "properties": {"action": {"type": "string", "enum": ["recover", "ambiguous", "none"]}, "candidate_id": {"type": "string"}, "reason": {"type": "string"}},
    "required": ["action", "candidate_id", "reason"],
    "additionalProperties": False,
}


class LLMClient:
    """Runs a structured gate LLM call (plain completion as fallback) and returns the parsed, logged JSON payload."""

    def __init__(self, llm_provider: LLMProvider, log_printer: LogPrinter) -> None:
        self._llm = llm_provider
        self._log = log_printer

    def primary(self, prompt: str, text: str) -> GateResult:
        data = self.complete(prompt, text, "command_gatekeeper", _PRIMARY_SCHEMA)
        if not data:
            return GateResult(False, "", 0.0)
        result = _gate_result(data)
        summary = f"classification={result.classification} directed={result.is_directed_at_tusk} text={result.cleaned_command!r} reason={str(data.get('reason', ''))!r}"
        self._log.log("GATEKEEPER", summary, "gatekeeper")
        return result

    def recovery(self, prompt: str, text: str, candidates: list[BufferedUtterance]) -> RecoveryDecision:
        data = self.complete(prompt, text, "command_gate_recovery", _RECOVERY_SCHEMA)
        decision = _recovery_decision(data, {item.id for item in candidates})
        summary = f"action={decision.action} candidate_id={decision.candidate_id!r} reason={decision.reason!r}"
        self._log.log("GATERECOVERY", summary, "gate-recovery")
        return decision

    def complete(self, prompt: str, text: str, name: str, schema: dict, max_tokens: int = 1024) -> dict[str, object]:
        raw = self._raw(prompt, text, name, schema, max_tokens)
        try:
            return extract_json_payload(raw) if raw else {}
        except ValueError as exc:
            self._log.log("ERROR", f"{name} parse error: {exc}", "gatekeeper")
            return {}

    def _raw(self, prompt: str, text: str, name: str, schema: dict, max_tokens: int) -> str:
        try:
            return self._llm.complete_structured(prompt, text, name, schema, max_tokens)
        except Exception as exc:
            self._log.log("ERROR", f"{name} structured output failed: {exc}", "gatekeeper")
        try:
            return self._llm.complete(prompt, text, max_tokens)
        except Exception as exc:
            self._log.log("ERROR", f"{name} fallback completion failed: {exc}")
            return ""


def _gate_result(data: dict[str, object]) -> GateResult:
    kind = _classification(data)
    directed = kind in (GateClassification.COMMAND, GateClassification.CONVERSATION)
    return GateResult(directed, str(data.get("cleaned_text", "")), 1.0, kind, str(data.get("intent", "")))


def _classification(data: dict[str, object]) -> GateClassification:
    try:
        return GateClassification(str(data.get("classification", "ambient")))
    except ValueError:
        return GateClassification.AMBIENT


def _recovery_decision(data: dict[str, object], valid_ids: set[str]) -> RecoveryDecision:
    decision = RecoveryDecision(str(data.get("action", "none")), str(data.get("candidate_id", "")), str(data.get("reason", "")))
    if decision.action == "recover" and decision.candidate_id not in valid_ids:
        return RecoveryDecision("none", reason="invalid candidate")
    return decision
