try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

from tusk.providers.llm.chat_completions_llm import ChatCompletionsLLM

__all__ = ["GroqLLM"]

_STRICT_SCHEMA_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b"})


class GroqLLM(ChatCompletionsLLM):
    def __init__(self, api_key: str, model: str) -> None:
        if Groq is None:
            raise RuntimeError("groq package is not installed")
        # the SDK's own silent 429 retries looked like 10-15 s LLM latency; LLMRetryRunner retries and logs instead
        client = Groq(api_key=api_key, timeout=30.0, max_retries=0)
        super().__init__(client, model, f"groq/{model}", self._response_format)

    def verify(self) -> None:
        # model listing costs no tokens; models.retrieve URL-encodes the slash in "openai/..." ids and Groq rejects it
        if self._model not in {model.id for model in self._client.models.list().data}:
            raise ValueError(f"groq does not serve {self._model}")

    def _response_format(self, schema_name: str, schema: dict) -> dict:
        if self._model in _STRICT_SCHEMA_MODELS:
            return {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
        return {"type": "json_object"}
