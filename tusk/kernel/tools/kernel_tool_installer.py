from tusk.kernel.tools.adapter_manager import AdapterManager
from tusk.kernel.core.kernel_api import KernelAPI
from tusk.kernel.modes.coding_mode import CodingMode
from tusk.kernel.modes.dictation_mode import DictationMode
from tusk.kernel.modes.editor.edit_applier import EditApplier
from tusk.kernel.modes.editor.editor_driver import EditorDriver
from tusk.kernel.modes.mode_slot import ModeSlot
from tusk.kernel.tools.start_coding_tool import StartCodingTool
from tusk.kernel.tools.start_dictation_tool import StartDictationTool
from tusk.kernel.tools.switch_model_tool import SwitchModelTool
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.llm.llm_registry import LLMRegistry
from tusk.shared.observability.status_reporter import StatusReporter

__all__ = ["KernelToolInstaller"]


class KernelToolInstaller:
    def __init__(self, tool_registry: ToolRegistry, llm_registry: LLMRegistry, adapter_manager: AdapterManager, log: LogPrinter, reporter: StatusReporter | None = None) -> None:
        self._registry = tool_registry
        self._llms = llm_registry
        self._manager = adapter_manager
        self._log = log
        self._reporter = reporter

    def install(self, kernel: KernelAPI) -> None:
        kernel.dictation.attach_mode(DictationMode(self._registry, self._log))
        self._register_coding(kernel.coding)
        self._registry.register(SwitchModelTool(self._llms, self._reporter))
        self._registry.register(StartDictationTool(self._registry, kernel.dictation, self._manager))

    def _register_coding(self, slot: ModeSlot) -> None:
        driver = EditorDriver(self._registry, self._manager.primary_desktop_source())
        slot.attach_mode(CodingMode(self._registry, driver, EditApplier(), self._log))
        self._registry.register(StartCodingTool(self._registry, slot, self._manager, driver))
