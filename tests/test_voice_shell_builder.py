import types

import voice_shell_builder
from tusk.providers.tts import OpenAICompatibleTTS
from tusk.shared.interrupt_token import InterruptToken
from voice_shell_builder import VoiceShellBuilder


def _config(tts_url: str = "", tts_enabled: bool = False) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        groq_api_key="k", tts_url=tts_url, tts_model="kokoro", tts_voice="am_michael", tts_enabled=tts_enabled,
        stt_engine="groq", whisper_model_size="base", stt_app_vocabulary=False, follow_up_timeout_seconds=30, ack_enabled=True,
    )


def _mode_kernel(requested: list[tuple]) -> types.SimpleNamespace:
    registry = types.SimpleNamespace(
        get=lambda name: requested.append(("get", name)) or object(),
        get_with_fallback=lambda name, fallback: requested.append(("fallback", name, fallback)) or object(),
    )
    return types.SimpleNamespace(
        llm_registry=registry, interrupt_token=InterruptToken(), submit=lambda text: None,
        dictation=_mode_slot(), coding=_mode_slot(),
    )


def _mode_slot() -> types.SimpleNamespace:
    return types.SimpleNamespace(set_callbacks=lambda on_start, on_stop: None, request_stop=lambda: None)


def _builder(config: types.SimpleNamespace, kernel: object | None = None) -> VoiceShellBuilder:
    return VoiceShellBuilder(config, kernel or _mode_kernel([]), types.SimpleNamespace(log=lambda *a: None))


def _patch_stt(monkeypatch, engine: object, seen: list[str] | None = None) -> None:
    def factory(key, size, vocabulary):
        if seen is not None:
            seen.append(vocabulary)
        return types.SimpleNamespace(create=lambda name: engine)
    monkeypatch.setattr("voice_shell_builder.STTEngineFactory", factory)


def test_builds_groq_tts_when_url_unset(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr("voice_shell_builder.GroqTTS", lambda key: sentinel)
    assert _builder(_config("")).tts_engine() is sentinel


def test_builds_openai_compatible_tts_when_url_set() -> None:
    engine = _builder(_config("http://kokoro:8880/v1/audio/speech")).tts_engine()
    assert isinstance(engine, OpenAICompatibleTTS)


def test_worker_receives_tts_engine_only_when_enabled(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr("voice_shell_builder.GroqTTS", lambda key: sentinel)
    assert _builder(_config(tts_enabled=True)).worker()._speaker._tts is sentinel
    assert _builder(_config(tts_enabled=False)).worker()._speaker._tts is None


def test_stt_engine_comes_from_factory() -> None:
    engine = _builder(_config()).stt_engine()
    assert engine.__class__.__name__ == "GroqSTT"


def test_vocabulary_is_computed_once_and_shared_by_stt_and_sanitizer(monkeypatch) -> None:
    calls: list[bool] = []
    vocabulary = types.SimpleNamespace(stt_prompt=lambda enabled: calls.append(enabled) or "Firefox GEdit")
    monkeypatch.setattr(voice_shell_builder.AppVocabulary, "installed", classmethod(lambda cls: vocabulary))
    seen: list[str] = []
    _patch_stt(monkeypatch, object(), seen)
    builder = _builder(_config())
    builder.stt_engine()
    sanitizer = builder.sanitizer(None)
    assert calls == [False] and seen == ["Firefox GEdit"]
    assert sanitizer._vocabulary_words == ["firefox", "gedit"]


def test_gatekeeper_wiring_resolves_stop_gate_slot_with_fallback() -> None:
    requested: list[tuple] = []
    worker = types.SimpleNamespace(is_busy=False, current_speech_text=None)
    slot = _builder(_config(), _mode_kernel(requested)).gatekeeper(worker)
    assert ("get", "gatekeeper") in requested and ("fallback", "stop_gate", "gatekeeper") in requested
    assert isinstance(slot._inner, voice_shell_builder.PlaybackGate)


def test_gatekeeper_tolerates_missing_registry() -> None:
    kernel = _mode_kernel([])
    kernel.llm_registry = None
    _builder(_config(), kernel).gatekeeper(types.SimpleNamespace(is_busy=False, current_speech_text=None))
