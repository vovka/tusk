from types import SimpleNamespace

from tusk.providers.llm.chat_completions_llm import ChatCompletionsLLM
from tusk.providers.llm.groq_llm import GroqLLM
from tusk.providers.llm.open_router_llm import OpenRouterLLM


def _capture_client(captured: dict) -> object:
    def create(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None))])

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_label_and_model_land_in_payload() -> None:
    captured: dict[str, object] = {}
    llm = ChatCompletionsLLM(_capture_client(captured), "m", "lab/m")
    assert llm.label == "lab/m"
    llm.complete_messages("sys", [{"role": "user", "content": "hi"}])
    assert captured["model"] == "m"
    assert captured["messages"][0] == {"role": "system", "content": "sys"}


def test_structured_uses_response_format_hook() -> None:
    captured: dict[str, object] = {}
    llm = ChatCompletionsLLM(_capture_client(captured), "m", "lab/m", lambda name, schema: {"type": name})
    llm.complete_structured("sys", "user", "json_object", {})
    assert captured["response_format"] == {"type": "json_object"}


def test_structured_without_hook_sends_no_response_format() -> None:
    captured: dict[str, object] = {}
    llm = OpenRouterLLM("key", "m")
    llm._client = _capture_client(captured)
    llm.complete_structured("sys", "user", "schema", {})
    assert "response_format" not in captured


def test_groq_strict_models_get_json_schema_format() -> None:
    captured: dict[str, object] = {}
    llm = GroqLLM("key", "openai/gpt-oss-120b")
    llm._client = _capture_client(captured)
    llm.complete_structured("sys", "user", "plan", {"type": "object"})
    assert captured["response_format"] == {"type": "json_schema", "json_schema": {"name": "plan", "strict": True, "schema": {"type": "object"}}}


def test_groq_other_models_get_json_object_format() -> None:
    captured: dict[str, object] = {}
    llm = GroqLLM("key", "llama")
    llm._client = _capture_client(captured)
    llm.complete_structured("sys", "user", "plan", {})
    assert captured["response_format"] == {"type": "json_object"}
