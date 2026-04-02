from dataclasses import dataclass

__all__ = ["AppEntry"]


@dataclass(frozen=True)
class AppEntry:
    name: str
    exec_cmd: str
