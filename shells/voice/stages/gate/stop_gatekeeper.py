import dataclasses
import re
from collections.abc import Callable

from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_action import GateAction
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.interfaces.gatekeeper import Gatekeeper
from shells.voice.stages.gate.gatekeeper_support import WAKE_WORDS
from tusk.shared.schemas.app_mode import MODE_BYPASS_KIND_PREFIX
from tusk.shared.schemas.utterance import Utterance

__all__ = ["StopGatekeeper"]

# "coating" is how STT hears "coding"; matched with or without wake word, so no LLM call is needed to leave the mode.
# Hyphenated ("pair-coding"), "paired/pear" and a filler word around the phrase are plausible STT outputs, not yet seen in takes.
_STOP_PHRASE = re.compile(
    r"(?:(?:ok|okay|please) )?"
    r"(?:(?:stop|exit|end|finish|leave|quit)(?: the)?(?: (?:pair|paired|pear))?[ -]?(?:coding|coating|programming|dictation)"
    r"(?: mode)?|done (?:coding|coating|dictating))(?: please| now)?"
)


class StopGatekeeper(Gatekeeper):
    """Forward-all gatekeeper for an active mode: only a stop intent or a wake-word command breaks the flow."""

    def __init__(self, gate: object, stop_callback: Callable[[], None], command_gatekeeper: Gatekeeper | None = None) -> None:
        self._gate = gate
        self._stop = stop_callback
        self._commands = command_gatekeeper

    def process(
        self,
        utterance: Utterance | BufferedUtterance,
        recent: list[Utterance],
        candidates: list[BufferedUtterance] | None = None,
    ) -> GateDispatch:
        text = utterance.text
        words = re.findall(r"[\w-]+", text.casefold())
        woken = bool(words) and words[0] in WAKE_WORDS
        if _STOP_PHRASE.fullmatch(" ".join(words[1:] if woken else words)):
            return self._stopped()
        if woken and self._commands is not None:
            return self._wake_word_command(utterance, recent, candidates)
        if self._gate.should_stop(text):
            return self._stopped()
        return GateDispatch(GateAction.FORWARD_CURRENT, text)

    def _wake_word_command(self, utterance: object, recent: list, candidates: list | None) -> GateDispatch:
        result = self._commands.process(utterance, recent, candidates)
        if result.action == GateAction.DROP or result.action == GateAction.INTERRUPT:
            return result
        return dataclasses.replace(result, kind=MODE_BYPASS_KIND_PREFIX + result.kind)

    def _stopped(self) -> GateDispatch:
        self._stop()
        return GateDispatch(GateAction.DROP)
