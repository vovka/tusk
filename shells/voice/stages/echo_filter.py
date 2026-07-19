import difflib
import time
from collections.abc import Callable

from shells.voice.stages.gate.gatekeeper_support import has_wake_word
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.utterance import Utterance

__all__ = ["EchoFilter"]

_WINDOW_SECONDS = 12.0
_SIMILARITY = 0.75
_SHORT_SIMILARITY = 0.95
_SHORT_LENGTH = 10
_MAX_ECHO_LENGTH_RATIO = 1.25


class EchoFilter:
    """Drops utterances that match what TUSK spoke recently — its own TTS echoed back through the mic."""

    # latency: a few difflib ratios on the pipeline thread per utterance; no LLM, no network

    def __init__(
        self,
        recent_speech: Callable[[], list[tuple[str, float]]],
        log_printer: LogPrinter | None = None,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._recent_speech = recent_speech
        self._log = log_printer
        self._now = now

    def process(self, utterance: Utterance) -> Utterance | None:
        # Spoken confirmations mirror the follow-up command about the same object, so a wake
        # word — which TUSK's own TTS never speaks — proves this is live speech, not an echo.
        if has_wake_word(utterance.text):
            return utterance
        spoken = self._recent_texts()
        if spoken and self._matches(_normalize(utterance.text), spoken):
            self._log_drop(utterance.text)
            return None
        return utterance

    def _recent_texts(self) -> list[str]:
        cutoff = self._now() - _WINDOW_SECONDS
        return [_normalize(text) for text, ended_at in self._recent_speech() if ended_at >= cutoff]

    def _matches(self, text: str, spoken: list[str]) -> bool:
        return any(_similar(text, candidate) for candidate in _contiguous_runs(spoken))

    def _log_drop(self, text: str) -> None:
        if self._log is not None:
            self._log.log("ECHOFLT", f"dropped reason=self-echo text={text!r}", "echo-filter")


def _contiguous_runs(spoken: list[str]) -> list[str]:
    # VAD/STT can merge adjacent spoken clips into one echo, so match every contiguous run, not just each clip
    runs: list[str] = []
    for start in range(len(spoken)):
        for end in range(start + 1, len(spoken) + 1):
            runs.append(" ".join(spoken[start:end]))
    return runs


def _normalize(text: str) -> str:
    return " ".join(text.lower().split()).strip(".,!?")


def _similar(text: str, candidate: str) -> bool:
    if not text or not candidate:
        return False
    # a much longer utterance is an echo merged with live speech, not a pure echo — let it through
    if len(text) > len(candidate) * _MAX_ECHO_LENGTH_RATIO:
        return False
    # short commands (stop, yes, play) collide easily, so demand a near-exact match before dropping one
    threshold = _SHORT_SIMILARITY if min(len(text), len(candidate)) < _SHORT_LENGTH else _SIMILARITY
    return difflib.SequenceMatcher(None, text, candidate).ratio() >= threshold
