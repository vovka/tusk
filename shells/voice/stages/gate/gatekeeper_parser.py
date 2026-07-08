from shells.voice.recovery_decision import RecoveryDecision
from tusk.shared.llm.llm_json import extract_json_payload
from tusk.shared.schemas.gate_classification import GateClassification
from tusk.shared.schemas.gate_result import GateResult

__all__ = ["parse_gate_result", "parse_recovery_decision"]


def parse_gate_result(raw: str) -> tuple[GateResult, str]:
    data = extract_json_payload(raw)
    reason = str(data.get("reason", ""))
    return _gate_result(data), reason


def parse_recovery_decision(raw: str) -> RecoveryDecision:
    data = extract_json_payload(raw)
    return RecoveryDecision(str(data.get("action", "none")), str(data.get("candidate_id", "")), str(data.get("reason", "")))


def _gate_result(data: dict) -> GateResult:
    kind = _classification(data)
    text = str(data.get("cleaned_text", ""))
    directed = kind in (GateClassification.COMMAND, GateClassification.CONVERSATION)
    return GateResult(directed, text, 1.0, kind)


def _classification(data: dict) -> GateClassification:
    try:
        return GateClassification(str(data.get("classification", "ambient")))
    except ValueError:
        return GateClassification.AMBIENT
