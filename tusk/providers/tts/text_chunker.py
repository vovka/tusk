__all__ = ["TextChunker"]


class TextChunker:
    def __init__(self, limit: int) -> None:
        self._limit = limit

    def split(self, text: str) -> list[str]:
        chunks: list[str] = []
        for word in text.split():
            self._add(chunks, word)
        return chunks or [text]

    def _add(self, chunks: list[str], word: str) -> None:
        if chunks and len(chunks[-1]) + 1 + len(word) <= self._limit:
            chunks[-1] = f"{chunks[-1]} {word}"
            return
        chunks.append(word)
