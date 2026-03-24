import types

import launcher.tusk_host_launcher as launcher
import main
from tusk.providers.configurable_llm_factory import ConfigurableLLMFactory
from tusk.providers.groq_llm import GroqLLM
from tusk.providers.groq_stt import GroqSTT
from tusk.providers.open_router_llm import OpenRouterLLM
from tusk.providers.whisper_stt import WhisperSTT


def test_provider_labels_and_factory() -> None:
    assert GroqLLM("k", "m").label == "groq/m"
    assert OpenRouterLLM("k", "m").label == "openrouter/m"
    fac = ConfigurableLLMFactory("g", "o")
    assert fac.create("groq", "m").label == "groq/m"


def test_stt_providers() -> None:
    audio = b"\x00\x00" * 200
    g = GroqSTT("k").transcribe(audio, 100)
    w = WhisperSTT("base").transcribe(audio, 100)
    assert g.duration_seconds > 0 and 0 <= w.confidence <= 1


def test_launcher_handle_and_main_helpers(monkeypatch) -> None:
    class Conn:
        out = b""
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def recv(self, n): return b"echo hi"
        def sendall(self, data): self.out = data
    conn = Conn()
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: None)
    launcher._handle(conn)
    assert conn.out == b"ok\n"
    cfg = types.SimpleNamespace(groq_api_key="k", openrouter_api_key="", gatekeeper_llm=types.SimpleNamespace(provider_name="groq", model="m"), agent_llm=types.SimpleNamespace(provider_name="groq", model="m"), utility_llm=types.SimpleNamespace(provider_name="groq", model="m"), audio_sample_rate=1, audio_frame_duration_ms=1, vad_aggressiveness=1, follow_up_timeout_seconds=1)
    assert main._build_llm_registry(cfg).slot_names == ["gatekeeper", "agent", "utility"]
