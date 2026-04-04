import types

from tusk.shared.llm import LLMProxy
from tusk.shared.schemas.tool_call import ToolCall


class LoggedProvider:
    label = "groq/model"

    def __init__(self, reply: object) -> None:
        self._reply = reply
        self._logger = None

    def set_payload_logger(self, logger: object) -> None:
        self._logger = logger

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        self._logger.before_request(self.label, _payload(system_prompt, user_message))
        return str(self._reply)

    def complete_tool_call(self, system_prompt: str, messages: list[dict], tools: list[dict[str, object]]) -> ToolCall:
        self._logger.before_request(self.label, {**_payload(system_prompt, messages[0]["content"]), "tools": tools, "tool_choice": "required"})
        return self._reply


def test_llm_proxy_logs_request_payload_wait_and_response_in_order() -> None:
    logged = []
    proxy = LLMProxy(LoggedProvider("assistant reply"), _proxy_log(logged), "agent", enabled_log_groups=_groups("llm-request", "llm-payload", "llm-response", "llm-wait"))
    proxy.complete("start " + ("x" * 220) + " finish", "hello")
    assert [item[:2] for item in logged] == [("log", "LLMREQUEST"), ("log", "LLMPAYLOAD"), ("wait", "groq/model"), ("clear",), ("log", "LLMRESPONSE")]
    assert '"slot"' not in logged[1][2]
    assert "chars more" in logged[1][2]
    assert '{ "role": "system", "content": "' in logged[1][2]


def test_llm_proxy_logs_tools_separately_and_full_modes_replace_compact() -> None:
    logged = []
    tools = [{"type": "function", "function": {"name": "done", "description": "Finish and return a result.", "parameters": {"type": "object"}}}]
    groups = _groups("llm-request", "llm-payload-full", "llm-tools-full", "llm-response-full", "llm-wait")
    proxy = LLMProxy(LoggedProvider(ToolCall("done", {"reply": "ok"}, "call-1")), _proxy_log(logged), "agent", enabled_log_groups=groups)
    proxy.complete_tool_call("sys", [{"role": "user", "content": "hello"}], tools)
    assert logged[2][:2] == ("log", "LLMTOOLS")
    assert logged[2][3] == "llm-tools-full"
    assert '"parameters": {' in logged[2][2]
    assert any(item[1] == "LLMRESPONSE" and item[3] == "llm-response-full" and '"call_id": "call-1"' in item[2] for item in logged if item[0] == "log")
    assert not any(item[3] == "llm-payload" for item in logged if item[0] == "log")


def test_llm_payload_keeps_text_when_truncation_saves_too_little() -> None:
    logged = []
    proxy = LLMProxy(LoggedProvider("assistant reply"), _proxy_log(logged), "agent", enabled_log_groups=_groups("llm-payload"), preview_chars=20)
    proxy.complete("Gedit has been opened successfully.", "hello")
    payload = next(item[2] for item in logged if item[0] == "log" and item[1] == "LLMPAYLOAD")
    assert "successfully." in payload
    assert "chars more" not in payload


def _payload(system_prompt: str, user_message: str) -> dict[str, object]:
    return {"model": "openai/gpt-oss-120b", "max_tokens": 1024, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]}


def _proxy_log(logged: list[tuple]) -> object:
    return types.SimpleNamespace(log=lambda *a: logged.append(("log", *a)), show_wait=lambda *a: logged.append(("wait", *a)), clear_wait=lambda: logged.append(("clear",)))


def _groups(*names: str) -> frozenset[str]:
    return frozenset(names)
