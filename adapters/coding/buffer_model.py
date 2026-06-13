from dataclasses import dataclass

__all__ = ["BufferModel"]


@dataclass(frozen=True)
class BufferModel:
    lines: tuple[str, ...]

    @classmethod
    def from_text(cls, text: str) -> "BufferModel":
        return cls(tuple(text.split("\n")))

    def to_text(self) -> str:
        return "\n".join(self.lines)

    def with_edit(self, edit: dict) -> "BufferModel":
        start = edit["target_start"] - 1
        end = edit["target_end"]
        if edit["kind"] == "insert":
            return self._spliced(start, start, edit.get("new_text", ""))
        if edit["kind"] == "delete":
            return self._spliced(start, end, "")
        return self._spliced(start, end, edit.get("new_text", ""))

    def _spliced(self, start: int, end: int, text: str) -> "BufferModel":
        replacement = tuple(text.split("\n")) if text else ()
        return BufferModel(self.lines[:start] + replacement + self.lines[end:])
