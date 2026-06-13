from dataclasses import dataclass

__all__ = ["BufferSelection"]


@dataclass(frozen=True)
class BufferSelection:
    start_line: int
    end_line: int
