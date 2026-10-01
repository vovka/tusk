from tusk.providers.tts import GroqTTS, OpenAICompatibleTTS

__all__ = ["TtsEngineBuilder"]


class TtsEngineBuilder:
    """Builds the TTS engine: an OpenAI-compatible server when TUSK_TTS_URL is set, otherwise Groq."""

    def __init__(self, config: object) -> None:
        self._config = config

    def build(self) -> object:
        if self._config.tts_url:
            return OpenAICompatibleTTS(self._config.tts_url, self._config.tts_model, self._config.tts_voice)
        return GroqTTS(self._config.groq_api_key)
