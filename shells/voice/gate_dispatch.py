from dataclasses import dataclass

__all__ = ["GateDispatch"]


@dataclass(frozen=True)
class GateDispatch:
    action: str
    text: str | None = None
    recovered_id: str = ""
