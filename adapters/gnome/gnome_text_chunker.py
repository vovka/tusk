__all__ = ["GnomeTextChunker"]

_MAX_CHARS = 300


class GnomeTextChunker:
    def split(self, text: str) -> list[str]:
        chunks: list[str] = []
        index = 0
        while index < len(text):
            chunks.append(text[index:index + _MAX_CHARS])
            index += _MAX_CHARS
        return chunks or [""]
