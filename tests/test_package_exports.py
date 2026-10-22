import tusk
import tusk.kernel as kernel
import tusk.kernel.agent.backends as backends
import tusk.kernel.interfaces as interfaces
import tusk.providers as providers
import tusk.providers.llm as llm_providers
import tusk.providers.stt as stt_providers
import tusk.shared as shared
import tusk.shared.config as config
import tusk.shared.interfaces as shared_interfaces
import tusk.shared.llm as llm
import tusk.shared.mcp as mcp
import tusk.shared.observability as observability
import tusk.shared.schemas as schemas
import tusk.shared.schemas.voice as voice_schemas


def test_root_and_kernel_exports_present() -> None:
    assert "shared" in tusk.__all__
    assert "providers" in tusk.__all__
    assert "lib" not in tusk.__all__
    assert "MainAgent" in kernel.__all__
    assert "Shell" in interfaces.__all__
    assert "ToolCall" in schemas.__all__
    assert {"GateDispatch", "BufferedUtterance", "Utterance"} <= set(voice_schemas.__all__)
    assert {"BackendRequest", "BackendResult"} <= set(backends.__all__)
    assert "AgentResult" not in backends.__all__


def test_shared_layer_exports_present() -> None:
    assert set(shared.__all__) == {"config", "interfaces", "llm", "mcp", "observability", "schemas"}
    assert "Config" in config.__all__
    assert "LLMProxy" in llm.__all__
    assert "LLMProvider" in shared_interfaces.__all__


def test_shared_nested_exports_present() -> None:
    assert "ColorLogPrinter" in observability.__all__
    assert "LogPrinter" in shared_interfaces.__all__
    assert "MCPClient" in mcp.__all__
    assert "STTEngine" in shared_interfaces.__all__


def test_provider_exports_present() -> None:
    assert "llm" in providers.__all__
    assert "stt" in providers.__all__
    assert "tts" in providers.__all__
    assert "ConfigurableLLMFactory" in llm_providers.__all__
    assert "GroqSTT" in stt_providers.__all__


def test_kernel_no_longer_reexports_infra() -> None:
    assert "Config" not in kernel.__all__
    assert "StartupOptions" not in kernel.__all__
    assert "LLMProxy" not in kernel.__all__
