import tusk.providers.stt as stt_providers
import tusk.shared.interfaces as interfaces


def test_shared_interfaces_export_every_abc() -> None:
    assert set(interfaces.__all__) == {
        "LLMProvider",
        "LLMProviderFactory",
        "LogPrinter",
        "STTEngine",
        "SpanHandle",
        "StatusSink",
        "TTSEngine",
        "Tracer",
    }


def test_stt_provider_exports_present() -> None:
    assert "GroqSTT" in stt_providers.__all__
    assert "WhisperSTT" in stt_providers.__all__
