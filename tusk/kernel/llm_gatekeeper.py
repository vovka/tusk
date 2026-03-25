import json

from tusk.kernel.interfaces.gatekeeper import Gatekeeper
from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.schemas.gate_result import GateResult
from tusk.kernel.schemas.utterance import Utterance

__all__ = ["LLMGatekeeper"]


class LLMGatekeeper(Gatekeeper):
    def __init__(self, llm_provider: LLMProvider, log_printer: LogPrinter) -> None:
        self._llm = llm_provider
        self._log = log_printer

    def evaluate(self, utterance: Utterance, system_prompt: str) -> GateResult:
        raw = self._llm.complete(system_prompt, utterance.text)
        self._log.log("LLM", f"[{self._llm.label}] gate → {raw!r}")
        try:
            data = json.loads(raw.strip().strip("`"))
        except json.JSONDecodeError:
            self._log.log("GATE", "parse error")
            return GateResult(False, "", 0.0)
        return GateResult(
            is_directed_at_tusk=bool(data.get("directed")),
            cleaned_command=data.get("cleaned_command", ""),
            confidence=1.0,
            metadata={k: str(v) for k, v in data.items() if k.startswith("metadata_")},
        )
