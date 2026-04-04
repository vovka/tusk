from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.llm.yaml_log_formatter import YamlLogFormatter

__all__ = ["LLMPayloadLogger"]


class LLMPayloadLogger:
    def __init__(self, log_printer: LogPrinter | None, slot_name: str, label_getter: object) -> None:
        self._log = log_printer
        self._slot = slot_name
        self._label = label_getter
        self._formatter = YamlLogFormatter()

    def log(self, system_prompt: str, messages: list[dict], response_format: dict | None = None, tools: list[dict[str, object]] | None = None) -> None:
        if self._log is None:
            return
        payload = self._payload(system_prompt, messages, response_format, tools)
        text = self._formatter.format(payload)
        self._log.log("LLMPAYLOAD", f"[{self._slot}] payload\n{text}", "llm-payload")

    def _payload(
        self,
        system_prompt: str,
        messages: list[dict],
        response_format: dict | None,
        tools: list[dict[str, object]] | None,
    ) -> dict[str, object]:
        payload = {"slot": self._slot, "provider": self._label(), "messages": self._messages(system_prompt, messages)}
        if response_format:
            payload["response_format"] = response_format
        if tools is not None:
            payload["tools"] = tools
        return payload

    def _messages(self, system_prompt: str, messages: list[dict]) -> list[dict]:
        return [{"role": "system", "content": system_prompt}, *messages]
