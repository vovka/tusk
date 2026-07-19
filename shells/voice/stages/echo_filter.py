import difflib
import string
import time
from collections.abc import Callable

from shells.voice.stages.gate.gatekeeper_support import WAKE_WORDS
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.utterance import Utterance

__all__ = ["EchoFilter"]

_WINDOW_SECONDS = 12.0
_SIMILARITY = 0.75
_IDENTITY_SIMILARITY = 0.95
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
        # A leading wake word forgives an utterance that merely mirrors recent speech, but not
        # one that is near-identical to it — a self-echoed TTS reply must still be dropped.
        match_ratio = self._best_match_ratio(_normalize(utterance.text))
        if match_ratio is None:
            return utterance
        if match_ratio < _IDENTITY_SIMILARITY and _starts_with_wake_word(utterance.text):
            return utterance
        self._log_drop(utterance.text)
        return None

    def _best_match_ratio(self, text: str) -> float | None:
        spoken = self._recent_texts()
        ratios = [ratio for run in _contiguous_runs(spoken) if (ratio := _match_ratio(text, run)) is not None]
        return max(ratios, default=None)

    def _recent_texts(self) -> list[str]:
        cutoff = self._now() - _WINDOW_SECONDS
        return [_normalize(text) for text, ended_at in self._recent_speech() if ended_at >= cutoff]

    def _log_drop(self, text: str) -> None:
        if self._log is not None:
            self._log.log("ECHOFLT", f"dropped reason=self-echo text={text!r}", "echo-filter")


def _starts_with_wake_word(text: str) -> bool:
    tokens = text.split()
    if not tokens:
        return False
    leading_word = tokens[0].strip(string.punctuation).lower()
    return leading_word in WAKE_WORDS


def _contiguous_runs(spoken: list[str]) -> list[str]:
    # VAD/STT can merge adjacent spoken clips into one echo, so match every contiguous run, not just each clip
    runs: list[str] = []
    for start in range(len(spoken)):
        for end in range(start + 1, len(spoken) + 1):
            runs.append(" ".join(spoken[start:end]))
    return runs


def _normalize(text: str) -> str:
    return " ".join(text.lower().split()).strip(".,!?")


def _match_ratio(text: str, candidate: str) -> float | None:
    if not text or not candidate:
        return None
    # a much longer utterance is an echo merged with live speech, not a pure echo — let it through
    if len(text) > len(candidate) * _MAX_ECHO_LENGTH_RATIO:
        return None
    # short commands (stop, yes, play) collide easily, so demand a near-exact match before dropping one
    threshold = _IDENTITY_SIMILARITY if min(len(text), len(candidate)) < _SHORT_LENGTH else _SIMILARITY
    ratio = difflib.SequenceMatcher(None, text, candidate).ratio()
    return ratio if ratio >= threshold else None
