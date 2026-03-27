from tusk.lib.llm.interfaces.llm_provider import LLMProvider
from tusk.lib.llm.interfaces.llm_provider_factory import LLMProviderFactory
from tusk.lib.llm.providers.groq_llm import GroqLLM
from tusk.lib.llm.providers.open_router_llm import OpenRouterLLM

__all__ = ["ConfigurableLLMFactory"]

_GROQ = "groq"
_OPENROUTER = "openrouter"


class ConfigurableLLMFactory(LLMProviderFactory):
    def __init__(self, groq_api_key: str, openrouter_api_key: str) -> None:
        self._keys: dict[str, str] = {
            _GROQ: groq_api_key,
            _OPENROUTER: openrouter_api_key,
        }

    def create(self, provider_name: str, model: str) -> LLMProvider:
        key = self._keys.get(provider_name, "")
        if not key:
            raise ValueError(f"no API key for provider: {provider_name}")
        return self._build(provider_name, key, model)

    def _build(self, provider_name: str, key: str, model: str) -> LLMProvider:
        if provider_name == _GROQ:
            return GroqLLM(key, model)
        if provider_name == _OPENROUTER:
            return OpenRouterLLM(key, model)
        raise ValueError(f"unknown provider: {provider_name}")
