from dataclasses import dataclass
from typing import Callable

from tusk.shared.schemas.tool_result import ToolResult

__all__ = ["RegisteredTool"]


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    input_schema: dict
    execute: Callable[[dict], ToolResult]
    source: str
    planner_visible: bool = True
    sequence_callable: bool = False
