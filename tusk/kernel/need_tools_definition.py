__all__ = ["NeedToolsDefinition"]


class NeedToolsDefinition:
    def build(self) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": "need_tools",
                "description": "Request replanning when the provided tool subset is insufficient.",
                "parameters": self._parameters(),
            },
        }

    def _parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "needed_capability": {"type": "string"},
            },
            "required": ["reason", "needed_capability"],
            "additionalProperties": False,
        }
