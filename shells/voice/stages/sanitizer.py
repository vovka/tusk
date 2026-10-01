import re

from shells.voice.stages.confirmation_reply import ConfirmationReply
from tusk.shared.desktop.fuzzy_name_matcher import FuzzyNameMatcher
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.utterance import Utterance

__all__ = ["Sanitizer"]

_MIN_DURATION = 0.4
_MAX_SHORT_WORD_LENGTH = 3
_PROMPT_ECHO_MIN_WORDS = 3
_PROMPT_ECHO_SHARE = 0.8
# A mangled echo keeps the prompt's shape: a long comma list where many items resemble prompt names.
_ECHO_LIST_MIN_ITEMS = 4
_ECHO_LIST_MAX_ITEM_WORDS = 3
_ECHO_LIST_SHARE = 0.5
_MIN_FUZZY_WORD_LENGTH = 3
_GHOST_PHRASES = {
    "thank you", "thanks", "thanks for watching", "thank you for watching",
    "thank you very much", "you", "bye", "bye bye", "okay", "ok", "oh",
    "uh", "um", "hmm", "so", "yeah", "yes", "no", "right", "sure", "well",
    "alright", "please subscribe", "like and subscribe", "see you next time",
    "the end", "good night", "good morning", "good evening", "hello", "hey", "hi",
}


class Sanitizer:
    def __init__(
        self,
        log_printer: LogPrinter | None = None,
        vocabulary: str = "",
        confirmation_reply: ConfirmationReply | None = None,
    ) -> None:
        self._log = log_printer
        self._vocabulary_words = sorted(set(_words(vocabulary)))
        self._matcher = FuzzyNameMatcher()
        self._confirmation_reply = confirmation_reply

    def process(self, utterance: Utterance) -> Utterance | None:
        reason = self._reason(utterance)
        if reason is not None:
            self._log_drop(reason, utterance.text)
            return None
        text = utterance.text.strip()
        self._log_pass(text)
        return utterance

    def _reason(self, utterance: Utterance) -> str | None:
        # a bare "yes"/"no" is a ghost phrase, except as the answer to a pending confirmation
        if self._confirmation_reply is not None and self._confirmation_reply.answer(utterance.text) is not None:
            return None
        if utterance.duration_seconds < _MIN_DURATION:
            return "short-duration"
        text = utterance.text.strip()
        return _reject(text) or self._prompt_echo(text)

    def _prompt_echo(self, text: str) -> str | None:
        # On silence Whisper "transcribes" its own vocabulary prompt; such junk must not reach the gatekeeper.
        words = _words(text)
        echoed = sum(self._echoes(word) for word in words)
        is_echo = len(words) >= _PROMPT_ECHO_MIN_WORDS and echoed >= _PROMPT_ECHO_SHARE * len(words)
        return "prompt-echo" if is_echo or self._echoed_list(text) else None

    def _echoed_list(self, text: str) -> bool:
        items = [_words(item) for item in text.split(",") if _words(item)]
        if len(items) < _ECHO_LIST_MIN_ITEMS or any(len(item) > _ECHO_LIST_MAX_ITEM_WORDS for item in items):
            return False
        echoed = sum(any(self._echoes(word) for word in item) for item in items)
        return echoed >= _ECHO_LIST_SHARE * len(items)

    def _echoes(self, word: str) -> bool:
        if word in self._vocabulary_words:
            return True
        return len(word) >= _MIN_FUZZY_WORD_LENGTH and self._matcher.closest(word, self._vocabulary_words) is not None

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


def _words(text: str) -> list[str]:
    return re.findall(r"[\w-]+", text.casefold())


def _normalize(text: str) -> str:
    return text.lower().rstrip(".!?,").strip()


def _punctuation_only(text: str) -> bool:
    return all(not char.isalnum() for char in text)


def _short_word(text: str) -> bool:
    words = text.split()
    return len(words) == 1 and len(words[0]) <= _MAX_SHORT_WORD_LENGTH
