from types import SimpleNamespace

from tusk.providers.llm.groq_llm import GroqLLM
from tusk.providers.llm.open_router_llm import OpenRouterLLM


def _canned_response() -> object:
    message = SimpleNamespace(content="ok", tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _capture_client(captured: dict) -> object:
    def create(**kwargs: object) -> object:
        captured.update(kwargs)
        return _canned_response()

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_groq_complete_honors_max_tokens() -> None:
    provider = GroqLLM("test-key", "test-model")
    captured: dict[str, object] = {}
    provider._client = _capture_client(captured)
    provider.complete("system", "user", max_tokens=64)
    assert captured["max_tokens"] == 64


def test_openrouter_complete_honors_max_tokens() -> None:
    provider = OpenRouterLLM("test-key", "test-model")
    captured: dict[str, object] = {}
    provider._client = _capture_client(captured)
    provider.complete("system", "user", max_tokens=64)
    assert captured["max_tokens"] == 64


def test_openrouter_structured_honors_max_tokens() -> None:
    provider = OpenRouterLLM("test-key", "test-model")
    captured: dict[str, object] = {}
    provider._client = _capture_client(captured)
    provider.complete_structured("system", "user", "schema", {}, max_tokens=96)
    assert captured["max_tokens"] == 96
