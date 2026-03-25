__all__ = ["TerminalToolDefinitionList"]


class TerminalToolDefinitionList:
    def build(self) -> list[dict[str, object]]:
        return [self._definition(*item) for item in self._items()]

    def _items(self) -> list[tuple[str, str]]:
        return [
            ("done", "Finish the request with a brief reply."),
            ("clarify", "Ask a short follow-up question when the request is ambiguous."),
            ("unknown", "Explain briefly why the request cannot be handled."),
        ]

    def _definition(self, name: str, description: str) -> dict[str, object]:
        return {
            "type": "function",
            "function": {"name": name, "description": description, "parameters": self._parameters(name)},
        }

    def _parameters(self, name: str) -> dict[str, object]:
        required = ["reply"] if name != "unknown" else ["reply", "reason"]
        return {"type": "object", "properties": self._properties(name), "required": required}

    def _properties(self, name: str) -> dict[str, object]:
        props = {"reply": {"type": "string"}}
        if name == "unknown":
            props["reason"] = {"type": "string"}
        return props
