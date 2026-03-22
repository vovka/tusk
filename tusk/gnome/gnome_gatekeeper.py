import json

from tusk.interfaces.gatekeeper import Gatekeeper
from tusk.interfaces.llm_provider import LLMProvider
from tusk.schemas.gate_result import GateResult
from tusk.schemas.utterance import Utterance

__all__ = ["GnomeGatekeeper"]

_SYSTEM_PROMPT = (
    "You are a gatekeeper for a voice assistant named TUSK. "
    "Decide if the transcribed speech is a command directed at TUSK. "
    "It is directed at TUSK if it mentions 'tusk' or is a clear imperative desktop command "
    "(e.g. 'open firefox', 'close this window'). "
    'Respond ONLY with valid JSON: {"directed": true, "cleaned_command": "<text>"} '
    'or {"directed": false, "cleaned_command": ""}. '
    "For cleaned_command, strip any leading 'tusk' or 'hey tusk' prefix and trim whitespace."
)


class GnomeGatekeeper(Gatekeeper):
    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    def evaluate(self, utterance: Utterance) -> GateResult:
        raw = self._llm.complete(_SYSTEM_PROMPT, utterance.text)
        print(f"[LLM:gate] {raw!r}")
        return self._parse_response(raw)

    def _extract_json(self, raw: str) -> str:
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip()
        return text

    def _unwrap(self, data: dict | list) -> dict:
        if isinstance(data, list):
            data = data[0]
        if "arguments" in data:
            data = data["arguments"]
        return data

    def _parse_response(self, raw: str) -> GateResult:
        try:
            data = self._unwrap(json.loads(self._extract_json(raw)))
            return GateResult(
                is_directed_at_tusk=bool(data["directed"]),
                cleaned_command=data.get("cleaned_command", ""),
                confidence=1.0,
            )
        except Exception as e:
            print(f"[GATE] parse error: {e}")
            return GateResult(is_directed_at_tusk=False, cleaned_command="", confidence=0.0)
