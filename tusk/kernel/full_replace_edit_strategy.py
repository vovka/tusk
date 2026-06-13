from tusk.kernel.interfaces.edit_application_strategy import EditApplicationStrategy
from tusk.kernel.interfaces.editor_driver import EditorDriver
from tusk.shared.schemas.edit_operation import EditOperation

__all__ = ["FullReplaceEditStrategy"]


class FullReplaceEditStrategy(EditApplicationStrategy):
    def apply(self, edit: EditOperation, driver: EditorDriver) -> None:
        driver.replace_buffer(edit.full_buffer)
