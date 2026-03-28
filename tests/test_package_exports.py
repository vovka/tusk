import tusk
import tusk.kernel as kernel
import tusk.kernel.interfaces as interfaces
import tusk.kernel.schemas as schemas
import tusk.lib.config as config
import tusk.lib.llm as llm
import tusk.lib.llm.interfaces as llm_interfaces
import tusk.lib.llm.providers as llm_providers
import tusk.lib.logging as logging
import tusk.lib.logging.interfaces as logging_interfaces
import tusk.lib.mcp as mcp
import tusk.lib.stt.interfaces as stt_interfaces
import tusk.lib.stt.providers as stt_providers


def test_root_and_kernel_exports_present() -> None:
    assert "lib" in tusk.__all__
    assert "MainAgent" in kernel.__all__
    assert "LLMTaskPlanner" in kernel.__all__
    assert "Shell" in interfaces.__all__
    assert "TaskPlanner" in interfaces.__all__
    assert "TaskPlan" in schemas.__all__


def test_lib_exports_present() -> None:
    assert "ColorLogPrinter" in logging.__all__
    assert "LogPrinter" in logging_interfaces.__all__
    assert "Config" in config.__all__
    assert "LLMProxy" in llm.__all__
    assert "LLMProvider" in llm_interfaces.__all__
    assert "ConfigurableLLMFactory" in llm_providers.__all__
    assert "STTEngine" in stt_interfaces.__all__
    assert "GroqSTT" in stt_providers.__all__
    assert "MCPClient" in mcp.__all__


def test_kernel_no_longer_reexports_infra() -> None:
    assert "Config" not in kernel.__all__
    assert "StartupOptions" not in kernel.__all__
    assert "LLMProxy" not in kernel.__all__
