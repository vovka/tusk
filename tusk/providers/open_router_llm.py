from openai import OpenAI

from tusk.interfaces.llm_provider import LLMProvider

__all__ = ["OpenRouterLLM"]

_BASE_URL = "https://openrouter.ai/api/v1"
_APP_HEADERS = {
    "HTTP-Referer": "https://github.com/vovka/tusk",
    "X-Title": "TUSK",
}


class OpenRouterLLM(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=_BASE_URL, default_headers=_APP_HEADERS)
        self._model = model

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        return self.complete_messages(system_prompt, [{"role": "user", "content": user_message}])

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        return response.choices[0].message.content
