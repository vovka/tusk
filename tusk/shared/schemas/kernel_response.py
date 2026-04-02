from dataclasses import dataclass

__all__ = ["KernelResponse"]


@dataclass(frozen=True)
class KernelResponse:
    handled: bool
    reply: str
