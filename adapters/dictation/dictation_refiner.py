import os

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

__all__ = ["DictationRefiner"]

_PROMPT = "Clean up dictated text. Return only the cleaned text."


class DictationRefiner:
    def refine(self, text: str) -> str:
        provider, model = os.environ.get("DICTATION_LLM", "groq/llama-3.1-8b-instant").split("/", 1)
        if provider == "groq":
            return self._groq_text(model, text)
        if provider == "openrouter":
            return self._openrouter_text(model, text)
        return text

    def _groq_text(self, model: str, text: str) -> str:
        if Groq is None or not os.environ.get("GROQ_API_KEY"):
            return text
        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        response = client.chat.completions.create(model=model, max_tokens=512, messages=self._messages(text))
        return response.choices[0].message.content.strip()

    def _openrouter_text(self, model: str, text: str) -> str:
        if OpenAI is None or not os.environ.get("OPENROUTER_API_KEY"):
            return text
        client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
        response = client.chat.completions.create(model=model, max_tokens=512, messages=self._messages(text))
        return response.choices[0].message.content.strip()

    def _messages(self, text: str) -> list[dict[str, str]]:
        return [{"role": "system", "content": _PROMPT}, {"role": "user", "content": text}]
