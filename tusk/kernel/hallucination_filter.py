from tusk.kernel.interfaces.utterance_filter import UtteranceFilter
from tusk.kernel.schemas.utterance import Utterance

__all__ = ["HallucinationFilter"]

_MIN_DURATION = 0.4
_MAX_SHORT_WORD_LENGTH = 3
_GHOST_PHRASES = {
    "thank you", "thanks", "thanks for watching", "thank you for watching",
    "thank you very much", "you", "bye", "bye bye", "okay", "ok", "oh",
    "uh", "um", "hmm", "so", "yeah", "yes", "no", "right", "sure", "well",
    "alright", "please subscribe", "like and subscribe", "see you next time",
    "the end", "good night", "good morning", "good evening", "hello", "hey", "hi",
}


class HallucinationFilter(UtteranceFilter):
    def is_valid(self, utterance: Utterance) -> bool:
        if utterance.duration_seconds < _MIN_DURATION:
            return False
        text = utterance.text.strip()
        return bool(text) and not _should_reject(text)


def _should_reject(text: str) -> bool:
    return _is_punctuation_only(text) or _normalize(text) in _GHOST_PHRASES or _is_short_single_word(text)


def _normalize(text: str) -> str:
    return text.lower().rstrip(".!?,").strip()


def _is_punctuation_only(text: str) -> bool:
    return all(not char.isalnum() for char in text)


def _is_short_single_word(text: str) -> bool:
    words = text.split()
    return len(words) == 1 and len(words[0]) <= _MAX_SHORT_WORD_LENGTH
