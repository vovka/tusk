try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

from tusk.kernel.interfaces.llm_provider import LLMProvider

__all__ = ["GroqLLM"]

_STRICT_SCHEMA_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b"})


class GroqLLM(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if Groq is None:
            raise RuntimeError("groq package is not installed")
        self._client = Groq(api_key=api_key, timeout=30.0)
        self._model = model

    @property
    def label(self) -> str:
        return f"groq/{self._model}"

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        return self.complete_messages(system_prompt, [{"role": "user", "content": user_message}])

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        return _message_content(response)

    def complete_structured(
        self,
        system_prompt: str,
        user_message: str,
        schema_name: str,
        schema: dict,
        max_tokens: int = 256,
    ) -> str:
        response = self._client.chat.completions.create(**self._structured_payload(
            system_prompt,
            user_message,
            schema_name,
            schema,
            max_tokens,
        ))
        return _message_content(response)

    def _structured_payload(
        self,
        system_prompt: str,
        user_message: str,
        schema_name: str,
        schema: dict,
        max_tokens: int,
    ) -> dict:
        return {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            "response_format": _response_format(self._model, schema_name, schema),
        }


def _response_format(model: str, schema_name: str, schema: dict) -> dict:
    if model in _STRICT_SCHEMA_MODELS:
        return {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
    return {"type": "json_object"}


def _message_content(response: object) -> str:
    content = response.choices[0].message.content
    if isinstance(content, str) and content.strip():
        return content
    raise RuntimeError("empty completion from groq provider")
