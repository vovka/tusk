from dataclasses import dataclass

__all__ = ["ToolResult"]


@dataclass(frozen=True)
class ToolResult:
    success: bool
    message: str
    data: dict | None = None
