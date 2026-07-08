from tusk.kernel.adapter_manager import AdapterManager
from tusk.kernel.modes.edit_strategies.full_replace_edit_strategy import FullReplaceEditStrategy
from tusk.kernel.modes.input_automation_editor_driver import InputAutomationEditorDriver
from tusk.kernel.modes.edit_strategies.line_anchored_edit_strategy import LineAnchoredEditStrategy
from tusk.kernel.modes.edit_strategies.verified_edit_strategy import VerifiedEditStrategy
from tusk.kernel.tools.internal_tools import CodingRouter, DictationRouter, StartCodingTool, StartDictationTool, SwitchModelTool
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.llm.llm_registry import LLMRegistry
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.status.interfaces.status_reporter import StatusReporter

__all__ = ["ToolRuntime"]


class ToolRuntime:
    def __init__(self, tool_registry: ToolRegistry, llm_registry: LLMRegistry, adapter_manager: AdapterManager, log: LogPrinter, reporter: StatusReporter | None = None) -> None:
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
        strategy = VerifiedEditStrategy(LineAnchoredEditStrategy(), FullReplaceEditStrategy())
        controller.attach_coding_router(CodingRouter(self._registry, controller, driver, strategy, self._log))
        self._registry.register(StartCodingTool(self._registry, controller, self._manager, driver))
