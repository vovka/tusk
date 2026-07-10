import json

__all__ = ["CodexResultParser"]


class CodexResultParser:
    """Extracts the schema-conforming payload from a `codex exec --json` stream.

    Codex emits one JSON event per line; the structured result is the JSON text
    of the final `item.completed` agent_message.
    """

    def parse(self, output: str) -> dict | None:
        text = self._last_agent_message(output)
        if text is None:
            return None
        payload = self._loads(text)
        return payload if isinstance(payload, dict) else None

    def _last_agent_message(self, output: str) -> str | None:
        found = None
        for line in output.splitlines():
            message = self._agent_message(line)
            if message is not None:
                found = message
        return found

    def _agent_message(self, line: str) -> str | None:
        event = self._loads(line)
        if not isinstance(event, dict) or event.get("type") != "item.completed":
            return None
        item = event.get("item") or {}
        if item.get("type") != "agent_message":
            return None
        return item.get("text")

    def _loads(self, raw: str) -> object | None:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
