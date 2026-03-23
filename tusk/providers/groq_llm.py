from groq import Groq

from tusk.interfaces.llm_provider import LLMProvider

__all__ = ["GroqLLM"]


class GroqLLM(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = Groq(api_key=api_key, timeout=10.0)
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
