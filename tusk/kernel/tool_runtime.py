from tusk.kernel.internal_tools import DictationRouter, StartDictationTool, SwitchModelTool

__all__ = ["ToolRuntime"]


class ToolRuntime:
    def __init__(self, tool_registry: object, llm_registry: object, adapter_manager: object, log: object) -> None:
        self._registry = tool_registry
        self._llms = llm_registry
        self._manager = adapter_manager
        self._log = log

    def register_tools(self, controller: object) -> None:
        controller.attach_dictation_router(DictationRouter(self._registry, controller, self._log))
        self._registry.register(SwitchModelTool(self._llms))
        self._registry.register(StartDictationTool(self._registry, controller, self._manager))
