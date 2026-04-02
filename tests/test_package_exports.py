import tusk
import tusk.kernel as kernel
import tusk.kernel.interfaces as interfaces
import tusk.providers as providers
import tusk.providers.llm as llm_providers
import tusk.providers.stt as stt_providers
import tusk.shared as shared
import tusk.shared.config as config
import tusk.shared.llm as llm
import tusk.shared.llm.interfaces as llm_interfaces
import tusk.shared.logging as logging
import tusk.shared.logging.interfaces as logging_interfaces
import tusk.shared.mcp as mcp
import tusk.shared.schemas as schemas
import tusk.shared.stt as stt
import tusk.shared.stt.interfaces as stt_interfaces


def test_root_and_kernel_exports_present() -> None:
    assert "shared" in tusk.__all__
    assert "providers" in tusk.__all__
    assert "lib" not in tusk.__all__
    assert "MainAgent" in kernel.__all__
    assert "Shell" in interfaces.__all__
    assert "ToolCall" in schemas.__all__


def test_shared_layer_exports_present() -> None:
    assert "llm" in shared.__all__
    assert "logging" in shared.__all__
    assert "schemas" in shared.__all__
    assert "stt" in shared.__all__
    assert "Config" in config.__all__
    assert "LLMProxy" in llm.__all__
    assert "LLMProvider" in llm_interfaces.__all__


def test_shared_nested_exports_present() -> None:
    assert "ColorLogPrinter" in logging.__all__
    assert "LogPrinter" in logging_interfaces.__all__
    assert "MCPClient" in mcp.__all__
    assert "interfaces" in stt.__all__
    assert "STTEngine" in stt_interfaces.__all__


def test_provider_exports_present() -> None:
    assert "llm" in providers.__all__
    assert "stt" in providers.__all__
    assert "ConfigurableLLMFactory" in llm_providers.__all__
    assert "GroqSTT" in stt_providers.__all__


def test_kernel_no_longer_reexports_infra() -> None:
    assert "Config" not in kernel.__all__
    assert "StartupOptions" not in kernel.__all__
    assert "LLMProxy" not in kernel.__all__
