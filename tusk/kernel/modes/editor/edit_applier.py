from tusk.kernel.modes.editor.editor_driver import EditorDriver
from tusk.shared.schemas.buffer_selection import BufferSelection
from tusk.shared.schemas.edit_operation import EditOperation

__all__ = ["EditApplier"]


class EditApplier:
    def apply(self, edit: EditOperation, driver: EditorDriver) -> None:
        self._apply_anchored(edit, driver)
        # Line-anchored edits drift under fire-and-forget GNOME automation
        # (gedit 46 dropped hunks), so the buffer is read back and compared
        # against the adapter's authoritative full_buffer; on mismatch it is
        # re-pasted whole. The read-back costs one clipboard round-trip (~0.4s) per edit.
        if not edit.full_buffer:
            return
        if driver.read_buffer() != edit.full_buffer:
            driver.replace_buffer(edit.full_buffer)

    def _apply_anchored(self, edit: EditOperation, driver: EditorDriver) -> None:
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
