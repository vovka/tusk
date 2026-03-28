import types

from tusk.lib.llm import LLMProxy, LLMRetryRunner
from tusk.kernel.schemas.tool_call import ToolCall


def test_llm_proxy_retries_transient_message_failures() -> None:
    calls = {"count": 0}
    proxy = LLMProxy(_messages_provider(calls), retry_runner=LLMRetryRunner(3, lambda *_: None))
    assert proxy.complete_messages("prompt", [{"role": "user", "content": "hi"}]) == '{"tool":"done","reply":"ok"}'
    assert calls["count"] == 2


def test_llm_proxy_does_not_retry_invalid_request_failures() -> None:
    calls = {"count": 0}
    proxy = LLMProxy(_invalid_provider(calls), retry_runner=LLMRetryRunner(3, lambda *_: None))
    try:
        proxy.complete_messages("prompt", [{"role": "user", "content": "hi"}])
    except RuntimeError as exc:
        assert "tool_use_failed" in str(exc)
    assert calls["count"] == 1


def test_llm_proxy_retries_structured_failures() -> None:
    calls = {"count": 0}
    proxy = LLMProxy(_structured_provider(calls), retry_runner=LLMRetryRunner(3, lambda *_: None))
    result = proxy.complete_structured("prompt", "hi", "gate", {"type": "object"}, 32)
    assert result == '{"classification":"command","cleaned_text":"hi","reason":"ok"}'
    assert calls["count"] == 2


def test_llm_proxy_retries_native_tool_calls() -> None:
    calls = {"count": 0}
    proxy = LLMProxy(_tool_provider(calls), retry_runner=LLMRetryRunner(3, lambda *_: None))
    result = proxy.complete_tool_call("prompt", [{"role": "user", "content": "hi"}], [])
    assert result.tool_name == "done" and calls["count"] == 2


def _messages_provider(calls: dict[str, int]) -> object:
    def complete_messages(*args):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("connection reset by peer")
        return '{"tool":"done","reply":"ok"}'

    return types.SimpleNamespace(label="agent", complete_messages=complete_messages)


def _invalid_provider(calls: dict[str, int]) -> object:
    def complete_messages(*args):
        calls["count"] += 1
        raise RuntimeError("tool_use_failed invalid_request_error")

    return types.SimpleNamespace(label="agent", complete_messages=complete_messages)


def _structured_provider(calls: dict[str, int]) -> object:
    def complete_structured(*args):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("503 service unavailable")
        return '{"classification":"command","cleaned_text":"hi","reason":"ok"}'

    return types.SimpleNamespace(label="gate", complete_structured=complete_structured)


def _tool_provider(calls: dict[str, int]) -> object:
    def complete_tool_call(*args):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("timed out")
        return ToolCall("done", {"reply": "ok"}, "call-1")

    return types.SimpleNamespace(label="agent", complete_tool_call=complete_tool_call)
