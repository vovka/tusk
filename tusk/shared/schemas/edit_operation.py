from dataclasses import dataclass

__all__ = ["EditOperation"]


@dataclass(frozen=True)
class EditOperation:
    kind: str
    target_start: int
    target_end: int
    new_text: str = ""
    full_buffer: str = ""
