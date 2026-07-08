import textwrap

__all__ = ["TextChunker"]


class TextChunker:
    def __init__(self, limit: int) -> None:
        self._limit = limit

    def split(self, text: str) -> list[str]:
        normalized = " ".join(text.split())
        chunks = textwrap.wrap(normalized, self._limit, break_long_words=False, break_on_hyphens=False)
        return chunks or [text]
