try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from tusk.providers.llm.chat_completions_llm import ChatCompletionsLLM

__all__ = ["OpenRouterLLM"]

_BASE_URL = "https://openrouter.ai/api/v1"
_APP_HEADERS = {"HTTP-Referer": "https://github.com/vovka/tusk", "X-Title": "TUSK"}


class OpenRouterLLM(ChatCompletionsLLM):
    # no response_format hook: OpenRouter structured output is plain completion with the schema in the prompt
    def __init__(self, api_key: str, model: str) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package is not installed")
        client = OpenAI(api_key=api_key, base_url=_BASE_URL, default_headers=_APP_HEADERS, timeout=15.0)
        super().__init__(client, model, f"openrouter/{model}")
