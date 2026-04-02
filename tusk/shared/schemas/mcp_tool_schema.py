from dataclasses import dataclass

__all__ = ["MCPToolSchema"]


@dataclass(frozen=True)
class MCPToolSchema:
    name: str
    description: str
    input_schema: dict
