from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.utterance import Utterance

__all__ = ["Sanitizer"]

_MIN_DURATION = 0.4
_MAX_SHORT_WORD_LENGTH = 3
_GHOST_PHRASES = {
    "thank you", "thanks", "thanks for watching", "thank you for watching",
    "thank you very much", "you", "bye", "bye bye", "okay", "ok", "oh",
    "uh", "um", "hmm", "so", "yeah", "yes", "no", "right", "sure", "well",
    "alright", "please subscribe", "like and subscribe", "see you next time",
    "the end", "good night", "good morning", "good evening", "hello", "hey", "hi",
}


class Sanitizer:
    def __init__(self, log_printer: LogPrinter | None = None) -> None:
        self._log = log_printer

    def process(self, utterance: Utterance) -> Utterance | None:
        reason = self._reason(utterance)
        if reason is not None:
            self._log_drop(reason, utterance.text)
            return None
        text = utterance.text.strip()
        self._log_pass(text)
        return utterance

    def _reason(self, utterance: Utterance) -> str | None:
        if utterance.duration_seconds < _MIN_DURATION:
            return "short-duration"
        text = utterance.text.strip()
        return _reject(text)

    def _log_drop(self, reason: str, text: str) -> None:
        if self._log:
            self._log.log("SANITIZER", f"dropped reason={reason} text={text!r}", "sanitizer")

    def _log_pass(self, text: str) -> None:
        if self._log:
            self._log.log("SANITIZER", f"passed text={text!r}", "sanitizer")


def _reject(text: str) -> str | None:
    if not text:
        return "empty"
    if _punctuation_only(text):
        return "punctuation-only"
    if _normalize(text) in _GHOST_PHRASES:
        return "ghost-phrase"
    return "short-word" if _short_word(text) else None


def _normalize(text: str) -> str:
    return text.lower().rstrip(".!?,").strip()


def _punctuation_only(text: str) -> bool:
    return all(not char.isalnum() for char in text)


def _short_word(text: str) -> bool:
    words = text.split()
    return len(words) == 1 and len(words[0]) <= _MAX_SHORT_WORD_LENGTH
