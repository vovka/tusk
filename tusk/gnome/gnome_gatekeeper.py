import json

from tusk.interfaces.gatekeeper import Gatekeeper
from tusk.interfaces.llm_provider import LLMProvider
from tusk.schemas.gate_result import GateResult
from tusk.schemas.utterance import Utterance

__all__ = ["GnomeGatekeeper"]


class GnomeGatekeeper(Gatekeeper):
    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    def evaluate(self, utterance: Utterance, system_prompt: str) -> GateResult:
        raw = self._llm.complete(system_prompt, utterance.text)
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
            return self._build_gate_result(data)
        except Exception as exc:
            print(f"[GATE] parse error: {exc}")
            return GateResult(is_directed_at_tusk=False, cleaned_command="", confidence=0.0)

    def _build_gate_result(self, data: dict) -> GateResult:
        metadata = {k: str(v) for k, v in data.items() if k.startswith("metadata_")}
        return GateResult(
            is_directed_at_tusk=bool(data["directed"]),
            cleaned_command=data.get("cleaned_command", ""),
            confidence=1.0,
            metadata=metadata,
        )
