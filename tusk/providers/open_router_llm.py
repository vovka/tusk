from openai import OpenAI

from tusk.interfaces.llm_provider import LLMProvider

__all__ = ["OpenRouterLLM"]

_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterLLM(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=_BASE_URL)
        self._model = model

    def complete(self, system_prompt: str, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=256,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content
