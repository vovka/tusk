import types

from composition import voice_shell_builder
from composition.voice_shell_builder import VoiceShellBuilder
from shells.voice.command_worker import CommandWorker
from shells.voice.voice_shell import VoiceShell
from tusk.providers.tts import OpenAICompatibleTTS
from tusk.shared.interrupt_token import InterruptToken


def _config(tts_url: str = "", tts_enabled: bool = False) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        groq_api_key="k", tts_url=tts_url, tts_model="kokoro", tts_voice="am_michael", tts_enabled=tts_enabled,
        stt_engine="groq", whisper_model_size="base", stt_app_vocabulary=False, follow_up_timeout_seconds=30, ack_enabled=True,
        audio_sample_rate=16000, audio_frame_duration_ms=30, vad_aggressiveness=2, vad_silence_ms=400,
        gate_recovery_window_seconds=60.0, gate_recovery_candidate_limit=6,
    )


def _kernel(requested: list[bool] | None = None) -> types.SimpleNamespace:
    registry = types.SimpleNamespace(get=lambda name: object(), get_with_fallback=lambda name, fallback: object())
    return types.SimpleNamespace(
        llm_registry=registry, interrupt_token=InterruptToken(), submit=lambda text, kind="conversation": None,
        request_interrupt=lambda: requested.append(True), dictation=_mode_slot(), coding=_mode_slot(),
    )


def _mode_slot() -> types.SimpleNamespace:
    return types.SimpleNamespace(set_callbacks=lambda on_start, on_stop: None, request_stop=lambda: None)


def _builder(config: types.SimpleNamespace, kernel: object | None = None, on_speech_end: object = None) -> VoiceShellBuilder:
    return VoiceShellBuilder(config, kernel or _kernel([]), types.SimpleNamespace(log=lambda *a: None), object(), on_speech_end)


def _patch_stt(monkeypatch, engine: object, seen: list[str] | None = None) -> None:
    def factory(key, size, vocabulary):
        if seen is not None:
            seen.append(vocabulary)
        return types.SimpleNamespace(create=lambda name: engine)
    monkeypatch.setattr("composition.voice_shell_builder.STTEngineFactory", factory)


def test_builds_groq_tts_when_url_unset(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr("composition.voice_shell_builder.GroqTTS", lambda key: sentinel)
    assert _builder(_config("")).tts_engine() is sentinel


def test_builds_openai_compatible_tts_when_url_set() -> None:
    engine = _builder(_config("http://kokoro:8880/v1/audio/speech")).tts_engine()
    assert isinstance(engine, OpenAICompatibleTTS)


def test_worker_receives_tts_engine_only_when_enabled(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr("composition.voice_shell_builder.GroqTTS", lambda key: sentinel)
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
    shell = _builder(_config()).build()
    assert calls == [False] and seen == ["Firefox GEdit"]
    assert shell._pipeline._sanitizer._vocabulary_words == ["firefox", "gedit"]


def test_build_wires_stt_worker_and_pause_gate_into_one_shell(monkeypatch) -> None:
    sentinel = object()
    _patch_stt(monkeypatch, sentinel)
    shell = _builder(_config()).build()
    assert isinstance(shell, VoiceShell) and isinstance(shell._worker, CommandWorker)
    assert shell._pipeline._transcriber._stt is sentinel
    assert shell._pause_gate.is_set() and shell._pipeline._detector._audio._pause_gate is shell._pause_gate


def test_build_passes_speech_end_callback_to_detector(monkeypatch) -> None:
    captured: dict = {}
    _patch_stt(monkeypatch, object())
    monkeypatch.setattr(voice_shell_builder, "UtteranceDetector", lambda *args, **kwargs: captured.update(kwargs))
    on_speech_end = lambda seconds_ago: None
    _builder(_config(), on_speech_end=on_speech_end).build()
    assert captured["on_speech_end"] is on_speech_end
    assert captured["silence_ms"] == 400


def test_interrupt_requests_kernel_interrupt_and_flushes_worker(monkeypatch) -> None:
    requested: list[bool] = []
    _patch_stt(monkeypatch, object())
    shell = _builder(_config(), _kernel(requested)).build()
    shell._worker.enqueue("queued command")
    shell._pipeline._on_interrupt()
    assert requested == [True]
    assert not shell._worker.is_busy
