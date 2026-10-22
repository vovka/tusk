import types
from unittest.mock import patch

from tusk.providers.llm.groq_llm import GroqLLM
from tusk.shared.llm import LLMPayloadLogger


def test_groq_tool_fallback_logs_both_payload_attempts() -> None:
    logged, llm = _fallback_case()
    llm.set_payload_logger(LLMPayloadLogger(_logger(logged), "agent", _groups("llm-payload-full", "llm-tools-full", "llm-wait")))
    llm.complete_tool_call("sys", [{"role": "user", "content": "hi"}], [{"type": "function", "function": {"name": "done", "description": "Finish."}}])
    payloads = [item for item in logged if item[1] == "LLMPAYLOAD"]
    assert len(payloads) == 2
    assert '"tool_choice": "required"' in payloads[0][2]
    assert '"tool_choice": "auto"' in payloads[1][2]


def _fallback_case() -> tuple[list[tuple], GroqLLM]:
    logged = []
    client = _client([RuntimeError("Tool choice is required and model did not call a tool"), _response("ok")])
    with patch("tusk.providers.llm.groq_llm.Groq", lambda **_: client):
        return logged, GroqLLM("key", "model")


def _client(responses: list[object]) -> object:
    def create(**_payload):
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))


def _logger(logged: list[tuple]) -> object:
    return types.SimpleNamespace(log=lambda *a: logged.append(("log", *a)), show_wait=lambda *a: logged.append(("wait", *a)), clear_wait=lambda: None)


def _groups(*names: str) -> frozenset[str]:
    return frozenset(names)


def _response(text: str) -> object:
    message = type("Message", (), {"tool_calls": [], "content": text})()
    choice = type("Choice", (), {"message": message})()
    return type("Response", (), {"choices": [choice]})()
