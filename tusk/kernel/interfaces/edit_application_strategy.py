from abc import ABC, abstractmethod

from tusk.kernel.interfaces.editor_driver import EditorDriver
from tusk.shared.schemas.edit_operation import EditOperation

__all__ = ["EditApplicationStrategy"]


class EditApplicationStrategy(ABC):
    @abstractmethod
    def apply(self, edit: EditOperation, driver: EditorDriver) -> None: ...
