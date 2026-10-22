import time
from collections.abc import Callable

from shells.voice.gate.command_gate_prompt import build_command_gate_prompt
from shells.voice.gate.gatekeeper_support import fallback_dispatch, recent_context, recovered_dispatch, recovery_worthwhile
from shells.voice.gate.llm_client import LLMClient
from shells.voice.gate.recovery_gate_prompt import build_recovery_gate_prompt
from shells.voice.gate.wake_words import has_wake_word, starts_with_wake_word
from shells.voice.interfaces.gatekeeper import Gatekeeper
from tusk.shared.interfaces.llm_provider import LLMProvider
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_action import GateAction
from tusk.shared.schemas.voice.gate_classification import GateClassification
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from tusk.shared.schemas.voice.gate_result import GateResult
from tusk.shared.schemas.voice.recovery_decision import RecoveryDecision
from tusk.shared.schemas.voice.utterance import Utterance

__all__ = ["LLMGatekeeper"]


class LLMGatekeeper(Gatekeeper):
    def __init__(
        self,
        llm_provider: LLMProvider,
        log_printer: LogPrinter,
        time_source: Callable[[], float] = time.monotonic,
        follow_up_window_seconds: float = 30.0,
        is_busy: Callable[[], bool] | None = None,
        current_speech_text: Callable[[], str | None] | None = None,
    ) -> None:
        self._client = LLMClient(llm_provider, log_printer)
        self._time = time_source
        self._window = follow_up_window_seconds
        self._is_busy = is_busy
        self._current_speech_text = current_speech_text
        self._last_forwarded_at: float | None = None

    def process(self, utterance: BufferedUtterance, recent: list[Utterance], candidates: list[BufferedUtterance]) -> GateDispatch:
        text = utterance.text
        primary = self._classify(text, recent)
        if self._interrupt_requested(primary):
            return GateDispatch(GateAction.INTERRUPT)
        dispatch = self._command_dispatch(primary, text)
        return dispatch or self._recovery_dispatch(text, recent, primary, candidates)

    def _classify(self, text: str, recent: list[Utterance]) -> GateResult:
        context = recent_context(recent) if self._within_follow_up_window() else ""
        prompt = build_command_gate_prompt(context, self._busy(), self._speaking())
        return self._client.primary(prompt, text)

    def _interrupt_requested(self, result: GateResult) -> bool:
        # honored only while busy: an idle "stop" keeps its normal classification path
        return result.classification == GateClassification.INTERRUPT and self._busy()

    def _busy(self) -> bool:
        return self._is_busy is not None and self._is_busy()

    def _speaking(self) -> str | None:
        return self._current_speech_text() if self._current_speech_text is not None else None

    def _command_dispatch(self, result: GateResult, text: str) -> GateDispatch | None:
        # a leading wake word is directed speech even when the LLM errs or calls it ambient
        woken = result.classification == GateClassification.AMBIENT and starts_with_wake_word(text)
        if result.classification != GateClassification.COMMAND and not woken:
            return None
        forward = GateDispatch(GateAction.FORWARD_CURRENT, result.cleaned_command or text, intent=result.intent, kind="command")
        return self._forward(forward)

    def _recovery_dispatch(self, text: str, recent: list[Utterance], primary: GateResult, candidates: list[BufferedUtterance]) -> GateDispatch:
        recovery = self._recover(text, recent, primary, candidates)
        if recovery.action == "recover":
            return self._forward(recovered_dispatch(candidates, recovery))
        if recovery.action == "ambiguous":
            return self._forward(GateDispatch(GateAction.FORWARD_CURRENT, text))
        dispatch = fallback_dispatch(primary, text, has_wake_word(text))
        return self._forward(dispatch) if dispatch.action == GateAction.FORWARD_CURRENT else dispatch

    def _recover(self, text: str, recent: list[Utterance], primary: GateResult, candidates: list[BufferedUtterance]) -> RecoveryDecision:
        if not recovery_worthwhile(text, primary, candidates):
            return RecoveryDecision("none")
        prompt = build_recovery_gate_prompt(recent_context(recent), candidates)
        return self._client.recovery(prompt, text, candidates)

    def _forward(self, dispatch: GateDispatch) -> GateDispatch:
        self._last_forwarded_at = self._time()
        return dispatch

    def _within_follow_up_window(self) -> bool:
        return self._last_forwarded_at is not None and self._time() - self._last_forwarded_at <= self._window
