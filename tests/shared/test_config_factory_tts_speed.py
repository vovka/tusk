from tusk.shared.config import ConfigFactory


def test_tts_speed_defaults_to_one(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("TTS_SPEED", raising=False)
    assert ConfigFactory().build().tts_speed == 1.0


def test_tts_speed_reads_env_var(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TTS_SPEED", "1.5")
    assert ConfigFactory().build().tts_speed == 1.5
