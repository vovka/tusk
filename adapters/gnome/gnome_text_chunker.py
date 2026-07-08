__all__ = ["GnomeTextChunker"]

_MAX_CHARS = 300


class GnomeTextChunker:
    def split(self, text: str) -> list[str]:
        return [text[index:index + _MAX_CHARS] for index in range(0, len(text), _MAX_CHARS)] or [""]
