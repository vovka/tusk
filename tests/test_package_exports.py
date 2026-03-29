import tusk
import tusk.kernel as kernel
import tusk.kernel.interfaces as interfaces
import tusk.kernel.schemas as schemas
import tusk.lib as lib
import tusk.lib.config as config
import tusk.lib.llm as llm
import tusk.lib.llm.interfaces as llm_interfaces
import tusk.lib.llm.providers as llm_providers
import tusk.lib.logging as logging
import tusk.lib.logging.interfaces as logging_interfaces
import tusk.lib.mcp as mcp


def test_root_and_kernel_exports_present() -> None:
    assert "lib" in tusk.__all__
    assert "MainAgent" in kernel.__all__
    assert "Shell" in interfaces.__all__
    assert "ToolCall" in schemas.__all__


def test_lib_agent_exports_present() -> None:
    assert "AgentOrchestrator" in lib.__all__
    assert "AgentRunRequest" in lib.__all__
    assert "FileAgentSessionStore" in lib.__all__


def test_lib_exports_present() -> None:
    assert "ColorLogPrinter" in logging.__all__
    assert "LogPrinter" in logging_interfaces.__all__
    assert "Config" in config.__all__
    assert "LLMProxy" in llm.__all__
    assert "LLMProvider" in llm_interfaces.__all__
    assert "ConfigurableLLMFactory" in llm_providers.__all__
    assert "MCPClient" in mcp.__all__


def test_kernel_no_longer_reexports_infra() -> None:
    assert "Config" not in kernel.__all__
    assert "StartupOptions" not in kernel.__all__
    assert "LLMProxy" not in kernel.__all__
