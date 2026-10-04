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
            # Whisper echoed the app list on silence and it did not fix app-name spelling, so it is opt-in.
            "stt_app_vocabulary": self._switch("STT_APP_VOCABULARY", "off"),
        }

    def _switch(self, name: str, default: str = "on") -> bool:
        return os.environ.get(name, default).lower() not in ("off", "0", "false")
