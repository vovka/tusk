from dataclasses import dataclass

__all__ = ["MCPToolResult"]


@dataclass(frozen=True)
class MCPToolResult:
    content: str
    is_error: bool = False
    data: dict | None = None
