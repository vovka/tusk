from dataclasses import dataclass

__all__ = ["DictationEdit"]


@dataclass(frozen=True)
class DictationEdit:
    operation: str
    text: str
    replace_chars: int = 0
