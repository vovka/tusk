from tusk.shared.config.speech_config_values import SpeechConfigValues


def test_tts_server_defaults_keep_groq_engine(monkeypatch) -> None:
    for name in ("TUSK_TTS_URL", "TUSK_TTS_MODEL", "TUSK_TTS_VOICE"):
        monkeypatch.delenv(name, raising=False)
    values = SpeechConfigValues().values()
    assert (values["tts_url"], values["tts_model"], values["tts_voice"]) == ("", "kokoro", "am_michael")


def test_tts_server_settings_read_from_env(monkeypatch) -> None:
    monkeypatch.setenv("TUSK_TTS_URL", "http://kokoro:8880/v1/audio/speech")
    monkeypatch.setenv("TUSK_TTS_MODEL", "tts-1")
    monkeypatch.setenv("TUSK_TTS_VOICE", "af_bella")
    values = SpeechConfigValues().values()
    assert (values["tts_url"], values["tts_model"], values["tts_voice"]) == (
        "http://kokoro:8880/v1/audio/speech", "tts-1", "af_bella",
    )
