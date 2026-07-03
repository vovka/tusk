import json
import re

__all__ = ["CodingEditPlanner"]

CODING_PLANNER_PROMPT = "\n".join([
    "You are the TUSK coding agent.",
    "You receive the current editor buffer, with each line numbered, and a spoken instruction describing a code change.",
    "The numbers and the '|' after them exist only so you can locate lines; never include them in your returned buffer.",
    "Return the complete, updated buffer with the instruction applied, containing only real code, no line-number prefixes.",
    "Preserve every line the instruction does not concern, exactly as given (its code content, not its line-number prefix).",
    "If the instruction names a line number that exists in the buffer, apply the change there.",
    "If it names a line number beyond the end of the buffer, ignore the exact number and place the change where it belongs structurally instead of padding with blank lines.",
    'Return strict JSON only: {"buffer":"..."}.',
])

_SCHEMA = {
    "type": "object",
    "properties": {"buffer": {"type": "string"}},
    "required": ["buffer"],
    "additionalProperties": False,
}

_MAX_TOKENS = 4096
_LINE_NUMBER_PREFIX = re.compile(r"^\d+\| ?")


class CodingEditPlanner:
    def __init__(self, llm: object) -> None:
        self._llm = llm

    def plan(self, intent: str, buffer_text: str) -> str | None:
        message = f"<buffer>\n{_numbered(buffer_text)}\n</buffer>\n<instruction>{intent}</instruction>"
        raw = self._llm.complete_structured(CODING_PLANNER_PROMPT, message, "coding_agent", _SCHEMA, _MAX_TOKENS)
        return self._parse(raw)

    def _parse(self, raw: str) -> str | None:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return None
        buffer = data.get("buffer") if isinstance(data, dict) else None
        return _unnumbered(buffer) if isinstance(buffer, str) else None


def _numbered(buffer_text: str) -> str:
    lines = buffer_text.split("\n")
    return "\n".join(f"{index}| {line}" for index, line in enumerate(lines, start=1))


def _unnumbered(buffer_text: str) -> str:
    return "\n".join(_LINE_NUMBER_PREFIX.sub("", line) for line in buffer_text.split("\n"))
