from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.recovery_decision import RecoveryDecision
from shells.voice.stages.gatekeeper_parser import parse_gate_result, parse_recovery_decision
from shells.voice.stages.gatekeeper_support import PRIMARY_SCHEMA, RECOVERY_SCHEMA, log_gate_result, log_recovery, normalize_recovery
from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas import GateResult

__all__ = ["GateLLMClient"]


class GateLLMClient:
    """Runs the gatekeeper LLM calls and turns raw output into parsed, logged results."""

    def __init__(self, llm_provider: LLMProvider, log_printer: LogPrinter) -> None:
        self._llm = llm_provider
        self._log = log_printer

    def primary(self, prompt: str, text: str) -> GateResult:
        return self._parsed_primary(self._complete(prompt, text, "command_gatekeeper", PRIMARY_SCHEMA))

    def recovery(self, prompt: str, text: str, candidates: list[BufferedUtterance]) -> RecoveryDecision:
        raw = self._complete(prompt, text, "command_gate_recovery", RECOVERY_SCHEMA)
        return self._parsed_recovery(raw, candidates)

    def _parsed_primary(self, raw: str) -> GateResult:
        if not raw:
            return GateResult(False, "", 0.0)
        try:
            result, reason = parse_gate_result(raw)
            log_gate_result(self._log, result, reason)
            return result
        except Exception as exc:
            self._log.log("ERROR", f"gatekeeper parse error: {exc}")
            return GateResult(False, "", 0.0)

    def _parsed_recovery(self, raw: str, candidates: list[BufferedUtterance]) -> RecoveryDecision:
        try:
            decision = parse_recovery_decision(raw) if raw else RecoveryDecision("none")
            item = normalize_recovery(decision, candidates)
            log_recovery(self._log, item)
            return item
        except Exception as exc:
            self._log.log("ERROR", f"gate recovery parse error: {exc}")
            return RecoveryDecision("none", reason="parse error")

    def _complete(self, prompt: str, text: str, name: str, schema: dict) -> str:
        try:
            return self._llm.complete_structured(prompt, text, name, schema, 512)
        except Exception as exc:
            self._log.log("GATEKEEPER", f"{name} structured output failed: {exc}", "gatekeeper")
        try:
            return self._llm.complete(prompt, text, 256)
        except Exception as exc:
            self._log.log("ERROR", f"{name} fallback completion failed: {exc}")
            return ""
