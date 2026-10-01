from dataclasses import dataclass

__all__ = ["AppEntry"]


@dataclass(frozen=True)
class AppEntry:
    name: str
    exec_cmd: str
    generic_name: str = ""
    keywords: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    desktop_id: str = ""
