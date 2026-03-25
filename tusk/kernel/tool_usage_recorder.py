from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["ToolUsageRecorder"]


class ToolUsageRecorder:
    def __init__(self, tool_registry: object, usage_store: object) -> None:
        self._registry = tool_registry
        self._store = usage_store

    def record(self, name: str, result: ToolResult) -> None:
        if not result.success or self._registry.is_broker(name):
            return
        self._store.record_success(name)
