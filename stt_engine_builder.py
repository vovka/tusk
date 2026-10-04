from adapters.gnome.app_vocabulary import AppVocabulary
from tusk.providers.stt import STTEngineFactory

__all__ = ["SttEngineBuilder"]


class SttEngineBuilder:
    """Builds the configured STT engine, biased toward installed application names."""

    def __init__(self, config: object) -> None:
        self._config = config

    def build(self) -> object:
        vocabulary = AppVocabulary.installed().stt_prompt(self._config.stt_app_vocabulary)
        factory = STTEngineFactory(self._config.groq_api_key, self._config.whisper_model_size, vocabulary)
        return factory.create(self._config.stt_engine)
