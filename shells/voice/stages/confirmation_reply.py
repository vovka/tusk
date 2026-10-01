import string
import time
from collections.abc import Callable

__all__ = ["ConfirmationReply"]

# Must match the kernel's confirmation question ("... Say 'Tusk, yes' to confirm.").
_QUESTION_MARKER = "to confirm"
_PENDING_SECONDS = 30.0
_WAKE_LIKE_WORDS = {"tusk", "task", "dusk", "tusks", "tsk", "hey"}
_ANSWERS = {"yes": "yes", "yeah": "yes", "confirm": "yes", "do it": "yes", "no": "no", "cancel": "no"}


class ConfirmationReply:
    """Recognises a spoken yes/no locally while TUSK's last utterance was a confirmation question."""

    # latency: string checks on the pipeline thread; lets the answer skip the gatekeeper LLM call

    def __init__(
        self,
        recent_speech: Callable[[], list[tuple[str, float]]],
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._recent_speech = recent_speech
        self._now = now

    def answer(self, text: str) -> str | None:
        if not self._pending():
            return None
        words = text.casefold().translate(str.maketrans("", "", string.punctuation)).split()
        while words and words[0] in _WAKE_LIKE_WORDS:
            words = words[1:]
        return _ANSWERS.get(" ".join(words))

    def _pending(self) -> bool:
        spoken = self._recent_speech()
        if not spoken:
            return False
        last_text, ended_at = spoken[-1]
        return _QUESTION_MARKER in last_text.casefold() and self._now() - ended_at <= _PENDING_SECONDS
