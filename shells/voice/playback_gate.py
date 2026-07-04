from collections.abc import Callable

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.interfaces.gatekeeper import Gatekeeper
from shells.voice.stages.command_gate_prompt import build_command_gate_prompt
from shells.voice.stages.gatekeeper_parser import parse_gate_result
from shells.voice.stages.gatekeeper_support import PRIMARY_SCHEMA, to_utterance
from tusk.shared.schemas.utterance import Utterance

__all__ = ["PlaybackGate"]


class PlaybackGate(Gatekeeper):
    def __init__(
        self, inner: Gatekeeper, llm_provider: object, log: object, current_speech_text: Callable[[], str | None]
    ) -> None:
        self._inner = inner
        self._llm = llm_provider
        self._log = log
        self._speech = current_speech_text

    def evaluate(self, utterance: Utterance, recent: list[Utterance]) -> object:
        return self._inner.evaluate(utterance, recent)

    def process(
        self,
        utterance: Utterance | BufferedUtterance,
        recent: list[Utterance],
        candidates: list[BufferedUtterance] | None = None,
    ) -> GateDispatch:
        speech = self._speech()
        if speech is None:
            return self._inner.process(utterance, recent, candidates)
        return self._interrupt_or_drop(to_utterance(utterance), speech)

    def _interrupt_or_drop(self, utterance: Utterance, speech: str) -> GateDispatch:
        result, _ = parse_gate_result(self._complete(utterance.text, speech))
        return GateDispatch("interrupt") if result.metadata.get("classification") == "interrupt" else GateDispatch("drop")

    def _complete(self, text: str, speech: str) -> str:
        prompt = build_command_gate_prompt("", True, speech)
        try:
            return self._llm.complete_structured(prompt, text, "playback_gate", PRIMARY_SCHEMA, 256)
        except Exception as exc:
            self._log.log("ERROR", f"playback gate failed: {exc}")
            return '{"classification":"ambient","cleaned_text":"","reason":"fallback"}'
