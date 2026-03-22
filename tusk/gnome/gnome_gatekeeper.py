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
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> GateResult:
        data = json.loads(raw.strip())
        return GateResult(
            is_directed_at_tusk=bool(data["directed"]),
            cleaned_command=data.get("cleaned_command", ""),
            confidence=1.0,
        )
