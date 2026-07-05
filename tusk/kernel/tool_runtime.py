from tusk.kernel.full_replace_edit_strategy import FullReplaceEditStrategy
from tusk.kernel.input_automation_editor_driver import InputAutomationEditorDriver
from tusk.kernel.internal_tools import CodingRouter, DictationRouter, StartCodingTool, StartDictationTool, SwitchModelTool

__all__ = ["ToolRuntime"]


class ToolRuntime:
    def __init__(self, tool_registry: object, llm_registry: object, adapter_manager: object, log: object, reporter: object | None = None) -> None:
        self._registry = tool_registry
        self._llms = llm_registry
        self._manager = adapter_manager
        self._log = log
        self._reporter = reporter

    def register_tools(self, controller: object) -> None:
        controller.attach_dictation_router(DictationRouter(self._registry, controller, self._log))
        self._register_coding(controller)
        self._registry.register(SwitchModelTool(self._llms, self._reporter))
        self._registry.register(StartDictationTool(self._registry, controller, self._manager))

    def _register_coding(self, controller: object) -> None:
        driver = InputAutomationEditorDriver(self._registry, self._manager.primary_desktop_source())
        controller.attach_coding_router(CodingRouter(self._registry, controller, driver, FullReplaceEditStrategy(), self._log))
        self._registry.register(StartCodingTool(self._registry, controller, self._manager, driver))
