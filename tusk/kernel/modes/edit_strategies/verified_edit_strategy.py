from tusk.kernel.interfaces.edit_application_strategy import EditApplicationStrategy
from tusk.kernel.interfaces.editor_driver import EditorDriver
from tusk.shared.schemas.edit_operation import EditOperation

__all__ = ["VerifiedEditStrategy"]


class VerifiedEditStrategy(EditApplicationStrategy):
    """Applies the primary strategy, then repairs drift with the fallback.

    Line-anchored edits drift under fire-and-forget GNOME automation
    (gedit 46 dropped hunks), so after each edit the buffer is read back
    and compared against the adapter's authoritative full_buffer; on
    mismatch the fallback re-applies it. The read-back costs one
    clipboard round-trip (~0.4s) per edit operation.
    """

    def __init__(self, primary: EditApplicationStrategy, fallback: EditApplicationStrategy) -> None:
        self._primary = primary
        self._fallback = fallback

    def apply(self, edit: EditOperation, driver: EditorDriver) -> None:
        self._primary.apply(edit, driver)
        if not edit.full_buffer:
            return
        if driver.read_buffer() != edit.full_buffer:
            self._fallback.apply(edit, driver)
