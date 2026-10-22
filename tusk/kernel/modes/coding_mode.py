from tusk.shared.schemas.edit_operation import EditOperation
from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.kernel.modes.editor.edit_applier import EditApplier
from tusk.kernel.modes.editor.editor_driver import EditorDriver
from tusk.kernel.modes.mode_state import ModeState
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.logging.interfaces.log_printer import LogPrinter

__all__ = ["CodingMode"]


class CodingMode:
    def __init__(self, tool_registry: ToolRegistry, driver: EditorDriver, applier: EditApplier, log_printer: LogPrinter) -> None:
        self._registry = tool_registry
        self._driver = driver
        self._applier = applier
        self._log = log_printer

    def process(self, state: ModeState, text: str) -> KernelResponse:
        result = self._intent_result(state, text)
        self._log.log("CODING", f"intent={text!r}")
        if not result.success or result.data is None:
            return KernelResponse(False, result.message)
        return self._apply(result)

    def _apply(self, result: ToolResult) -> KernelResponse:
        try:
            self._apply_all(result.data.get("operations", []))
        except (RuntimeError, KeyError, TypeError, AttributeError) as exc:
            self._log.log("CODING", f"apply failed: {exc}")
            return KernelResponse(False, "I couldn't apply that edit.")
        return KernelResponse(True, "")

    def stop(self, state: ModeState) -> KernelResponse:
        self._registry.get(f"{state.adapter_name}.stop_coding_session").execute({"session_id": state.session_id})
        return KernelResponse(True, "Coding stopped.")

    def _intent_result(self, state: ModeState, text: str) -> ToolResult:
        name = f"{state.adapter_name}.process_intent"
        return self._registry.get(name).execute({"session_id": state.session_id, "intent": text})

    def _apply_all(self, operations: list[dict]) -> None:
        for operation in operations:
            self._applier.apply(self._to_operation(operation), self._driver)

    def _to_operation(self, data: dict) -> EditOperation:
        return EditOperation(data["kind"], data["target_start"], data["target_end"], data.get("new_text", ""), data.get("full_buffer", ""))
