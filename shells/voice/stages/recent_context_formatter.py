from tusk.shared.schemas.utterance import Utterance

__all__ = ["RecentContextFormatter"]

_DEFAULT_MAX_UTTERANCES = 6
_MAX_CONTENT_LENGTH = 150


class RecentContextFormatter:
    def __init__(self, max_utterances: int = _DEFAULT_MAX_UTTERANCES) -> None:
        self._max = max_utterances

    def format(self, utterances: list[Utterance]) -> str:
        recent = [item for item in utterances if item.text.strip()][-self._max:]
        if not recent:
            return ""
        return "\n".join(self._line(item) for item in recent)

    def _line(self, utterance: Utterance) -> str:
        return f"User: {utterance.text[:_MAX_CONTENT_LENGTH]}"
