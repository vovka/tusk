from tusk.providers.tts import GroqTTS


def test_groq_tts_synthesizes_wav_bytes() -> None:
    assert GroqTTS("test-key").synthesize("hello there") == b"WAVDATA"
