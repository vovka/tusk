from tusk.shared.schemas.edit_operation import EditOperation
from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["CodingRouter"]


class CodingRouter:
    def __init__(self, tool_registry: object, controller: object, driver: object, strategy: object, log_printer: object) -> None:
        self._registry = tool_registry
        self._controller = controller
        self._driver = driver
        self._strategy = strategy
        self._log = log_printer

    def process(self, state: object, text: str) -> KernelResponse:
        result = self._intent_result(state, text)
        self._log.log("CODING", f"intent={text!r}")
        if not result.success or result.data is None:
            return KernelResponse(False, result.message)
        self._apply_all(result.data.get("operations", []))
        return KernelResponse(True, result.message)

    def stop(self, state: object) -> KernelResponse:
        self._registry.get(f"{state.adapter_name}.stop_coding_session").execute({"session_id": state.session_id})
        self._controller.stop_coding()
        return KernelResponse(True, "Coding stopped.")

    def _intent_result(self, state: object, text: str) -> object:
        name = f"{state.adapter_name}.process_intent"
        return self._registry.get(name).execute({"session_id": state.session_id, "intent": text})

    def _apply_all(self, operations: list[dict]) -> None:
        for operation in operations:
            self._strategy.apply(self._to_operation(operation), self._driver)

    def _to_operation(self, data: dict) -> EditOperation:
        return EditOperation(data["kind"], data["target_start"], data["target_end"], data.get("new_text", ""), data.get("full_buffer", ""))
