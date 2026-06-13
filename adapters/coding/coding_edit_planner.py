import json

__all__ = ["CodingEditPlanner"]

CODING_PLANNER_PROMPT = "\n".join([
    "You are the TUSK coding agent.",
    "You receive the current editor buffer and a spoken instruction describing a code change.",
    "Return structured edit operations that realize the instruction against the buffer.",
    "Line numbers are 1-based and inclusive. Each operation is insert, replace, or delete.",
    "For insert and replace, new_text is the literal code. For delete, new_text is empty.",
    'Return strict JSON only: {"operations":[{"kind":"...","target_start":N,"target_end":N,"new_text":"..."}]}.',
])

_SCHEMA = {
    "type": "object",
    "properties": {
        "operations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string"},
                    "target_start": {"type": "integer"},
                    "target_end": {"type": "integer"},
                    "new_text": {"type": "string"},
                },
                "required": ["kind", "target_start", "target_end", "new_text"],
            },
        }
    },
    "required": ["operations"],
}


class CodingEditPlanner:
    def __init__(self, llm: object) -> None:
        self._llm = llm

    def plan(self, intent: str, buffer_text: str) -> list[dict]:
        message = f"<buffer>\n{buffer_text}\n</buffer>\n<instruction>{intent}</instruction>"
        return self._parse(self._llm.complete_structured(CODING_PLANNER_PROMPT, message, "coding_agent", _SCHEMA, 1024))

    def _parse(self, raw: str) -> list[dict]:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return []
        return data.get("operations", []) if isinstance(data, dict) else []
