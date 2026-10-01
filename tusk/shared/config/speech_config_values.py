import os

__all__ = ["SpeechConfigValues"]


class SpeechConfigValues:
    """Reads the spoken-reply settings (TTS on/off, optional OpenAI-compatible server, ack)."""

    def values(self) -> dict:
        return {
            "tts_enabled": self._switch("TUSK_TTS"),
            "tts_url": os.environ.get("TUSK_TTS_URL", ""),
            "tts_model": os.environ.get("TUSK_TTS_MODEL", "kokoro"),
            "tts_voice": os.environ.get("TUSK_TTS_VOICE", "am_michael"),
            "ack_enabled": self._switch("TUSK_ACK"),
        }

    def _switch(self, name: str) -> bool:
        return os.environ.get(name, "on").lower() not in ("off", "0", "false")
