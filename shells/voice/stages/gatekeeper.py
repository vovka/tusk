import time

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.interfaces.gatekeeper import Gatekeeper
from shells.voice.recovery_decision import RecoveryDecision
from shells.voice.stages.command_gate_prompt import build_command_gate_prompt
from shells.voice.stages.gatekeeper_parser import parse_gate_result, parse_recovery_decision
from shells.voice.stages.gatekeeper_support import PRIMARY_SCHEMA, RECOVERY_SCHEMA, fallback_dispatch, has_wake_word, log_gate_result, log_recovery, normalize_recovery, recovered_dispatch, to_utterance
from shells.voice.stages.recent_context_formatter import RecentContextFormatter
from shells.voice.stages.recovery_gate_prompt import build_recovery_gate_prompt
from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas import GateResult, Utterance

__all__ = ["LLMGatekeeper"]


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
        prompt = build_command_gate_prompt(self._formatter.format(recent) if self._within_follow_up_window() else "")
        return self._parsed_primary(self._complete(prompt, utterance.text, "command_gatekeeper", PRIMARY_SCHEMA))

    def process(
        self,
        utterance: Utterance | BufferedUtterance,
        recent: list[Utterance],
        candidates: list[BufferedUtterance] | None = None,
    ) -> GateDispatch:
        current = to_utterance(utterance)
        primary = self.evaluate(current, recent)
        dispatch = self._command_dispatch(primary, current)
        return dispatch or self._recovery_dispatch(current, recent, primary, candidates or [])

    def _command_dispatch(self, result: GateResult, utterance: Utterance) -> GateDispatch | None:
        if result.metadata.get("classification") != "command":
            return None
        return self._forward(GateDispatch("forward_current", result.cleaned_command or utterance.text))

    def _recovery_dispatch(
        self,
        utterance: Utterance,
        recent: list[Utterance],
        primary: GateResult,
        candidates: list[BufferedUtterance],
    ) -> GateDispatch:
        recovery = self._recover(utterance, recent, candidates)
        if recovery.action == "recover":
            return self._forward(recovered_dispatch(candidates, recovery))
        if recovery.action == "ambiguous":
            return self._forward(GateDispatch("forward_clarification", utterance.text))
        dispatch = fallback_dispatch(primary, utterance, has_wake_word(utterance.text))
        return self._forward(dispatch) if dispatch.action == "forward_current" else dispatch

    def _recover(self, utterance: Utterance, recent: list[Utterance], candidates: list[BufferedUtterance]) -> RecoveryDecision:
        if not candidates:
            return RecoveryDecision("none")
        prompt = build_recovery_gate_prompt(self._formatter.format(recent), candidates)
        raw = self._complete(prompt, utterance.text, "command_gate_recovery", RECOVERY_SCHEMA)
        return self._parsed_recovery(raw, candidates)

    def _parsed_primary(self, raw: str) -> GateResult:
        if not raw:
            return GateResult(False, "", 0.0)
        try:
            result, reason = parse_gate_result(raw)
            log_gate_result(self._log, result, reason)
            return result
        except Exception as exc:
            self._log.log("GATEKEEPER", f"parse error: {exc}", "gatekeeper")
            return GateResult(False, "", 0.0)

    def _parsed_recovery(self, raw: str, candidates: list[BufferedUtterance]) -> RecoveryDecision:
        try:
            decision = parse_recovery_decision(raw) if raw else RecoveryDecision("none")
            item = normalize_recovery(decision, candidates)
            log_recovery(self._log, item)
            return item
        except Exception as exc:
            self._log.log("GATERECOVERY", f"parse error: {exc}", "gate-recovery")
            return RecoveryDecision("none", reason="parse error")

    def _complete(self, prompt: str, text: str, name: str, schema: dict) -> str:
        try:
            return self._llm.complete_structured(prompt, text, name, schema, 512)
        except Exception as exc:
            self._log.log("GATEKEEPER", f"{name} structured output failed: {exc}", "gatekeeper")
        try:
            return self._llm.complete(prompt, text, 256)
        except Exception as exc:
            self._log.log("GATEKEEPER", f"{name} fallback completion failed: {exc}", "gatekeeper")
            return ""

    def _forward(self, dispatch: GateDispatch) -> GateDispatch:
        self._last_forwarded_at = self._time()
        return dispatch

    def _within_follow_up_window(self) -> bool:
        return self._last_forwarded_at is not None and self._time() - self._last_forwarded_at <= self._window
