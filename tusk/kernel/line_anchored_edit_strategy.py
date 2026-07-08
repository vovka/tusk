from tusk.kernel.interfaces.edit_application_strategy import EditApplicationStrategy
from tusk.kernel.interfaces.editor_driver import EditorDriver
from tusk.shared.schemas.buffer_selection import BufferSelection
from tusk.shared.schemas.edit_operation import EditOperation

__all__ = ["LineAnchoredEditStrategy"]


class LineAnchoredEditStrategy(EditApplicationStrategy):
    def apply(self, edit: EditOperation, driver: EditorDriver) -> None:
        if edit.kind == "insert":
            return self._insert(edit, driver)
        if edit.kind == "delete":
            return self._delete(edit, driver)
        return self._replace(edit, driver)

    def _insert(self, edit: EditOperation, driver: EditorDriver) -> None:
        driver.goto_line(edit.target_start)
        driver.paste(edit.new_text)

    def _replace(self, edit: EditOperation, driver: EditorDriver) -> None:
        driver.select_range(BufferSelection(edit.target_start, edit.target_end))
        driver.paste(edit.new_text)

    def _delete(self, edit: EditOperation, driver: EditorDriver) -> None:
        driver.select_range(BufferSelection(edit.target_start, edit.target_end))
        driver.press_keys("Delete")
