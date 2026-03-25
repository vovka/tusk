from dataclasses import dataclass

__all__ = ["MCPToolResult", "MCPToolSchema"]


@dataclass(frozen=True)
class MCPToolSchema:
    name: str
    description: str
    input_schema: dict


@dataclass(frozen=True)
class MCPToolResult:
    content: str
    is_error: bool = False
    data: dict | None = None
