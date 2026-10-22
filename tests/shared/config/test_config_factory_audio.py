from tusk.shared.config import ConfigFactory


def test_vad_silence_defaults_to_400_ms(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("VAD_SILENCE_MS", raising=False)
    assert ConfigFactory().build().vad_silence_ms == 400


def test_vad_silence_is_read_from_env(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("VAD_SILENCE_MS", "600")
    assert ConfigFactory().build().vad_silence_ms == 600


def test_stt_app_vocabulary_defaults_off(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("STT_APP_VOCABULARY", raising=False)
    assert ConfigFactory().build().stt_app_vocabulary is False


def test_stt_app_vocabulary_is_read_from_env(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("STT_APP_VOCABULARY", "on")
    assert ConfigFactory().build().stt_app_vocabulary is True


def test_tts_server_defaults_keep_groq_engine(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    for name in ("TUSK_TTS_URL", "TUSK_TTS_MODEL", "TUSK_TTS_VOICE"):
        monkeypatch.delenv(name, raising=False)
    config = ConfigFactory().build()
    assert (config.tts_url, config.tts_model, config.tts_voice) == ("", "kokoro", "am_michael")


def test_tts_server_settings_read_from_env(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TUSK_TTS_URL", "http://kokoro:8880/v1/audio/speech")
    monkeypatch.setenv("TUSK_TTS_MODEL", "tts-1")
    monkeypatch.setenv("TUSK_TTS_VOICE", "af_bella")
    config = ConfigFactory().build()
    assert (config.tts_url, config.tts_model, config.tts_voice) == (
        "http://kokoro:8880/v1/audio/speech", "tts-1", "af_bella",
    )
