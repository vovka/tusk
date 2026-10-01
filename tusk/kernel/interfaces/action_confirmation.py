from abc import ABC, abstractmethod

from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.tools.tool_result import ToolResult

__all__ = ["ActionConfirmation"]


class ActionConfirmation(ABC):
    @abstractmethod
    def execute(self, tool_name: str, arguments: dict[str, object]) -> ToolResult:
        ...

    @abstractmethod
    def resolve(self, text: str) -> KernelResponse | None:
        ...

    @abstractmethod
    def take_question(self) -> str | None:
        ...
