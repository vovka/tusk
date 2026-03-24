from abc import ABC, abstractmethod

from tusk.schemas.tool_result import ToolResult

__all__ = ["AgentTool"]


class AgentTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def parameters_schema(self) -> dict[str, str]:
        ...

    @abstractmethod
    def execute(self, parameters: dict[str, str]) -> ToolResult:
        ...
