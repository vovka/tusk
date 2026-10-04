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


def test_groq_client_leaves_retries_to_the_logged_retry_runner(monkeypatch: object) -> None:
    import tusk.providers.llm.groq_llm as groq_llm
    client_kwargs: dict[str, object] = {}
    monkeypatch.setattr(groq_llm, "Groq", lambda **kwargs: client_kwargs.update(kwargs))
    GroqLLM("test-key", "test-model")
    assert client_kwargs["max_retries"] == 0


def _listing_client(*ids: str) -> object:
    listing = SimpleNamespace(data=[SimpleNamespace(id=model_id) for model_id in ids])
    return SimpleNamespace(models=SimpleNamespace(list=lambda: listing))


def test_groq_verify_accepts_slashed_model_id_from_listing() -> None:
    # models.retrieve URL-encodes the slash (openai%2Fgpt-oss-20b) and Groq rejects it, so even in-use ids failed
    provider = GroqLLM("test-key", "openai/gpt-oss-120b")
    provider._client = _listing_client("openai/gpt-oss-20b", "openai/gpt-oss-120b")
    provider.verify()


def test_groq_verify_rejects_unlisted_model() -> None:
    import pytest
    provider = GroqLLM("test-key", "gpt-oss")
    provider._client = _listing_client("openai/gpt-oss-120b")
    with pytest.raises(ValueError):
        provider.verify()
