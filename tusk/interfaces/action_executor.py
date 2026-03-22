from abc import ABC, abstractmethod

from tusk.schemas.semantic_action import SemanticAction

__all__ = ["ActionExecutor"]


class ActionExecutor(ABC):
    @abstractmethod
    def execute(self, action: SemanticAction) -> None:
        ...
