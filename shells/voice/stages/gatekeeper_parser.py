import json

from shells.voice.recovery_decision import RecoveryDecision
from tusk.shared.schemas.gate_result import GateResult

__all__ = ["parse_gate_result", "parse_recovery_decision"]


def parse_gate_result(raw: str) -> tuple[GateResult, str]:
    data = _decoded(raw)
    reason = str(data.get("reason", ""))
    return _gate_result(data), reason


def parse_recovery_decision(raw: str) -> RecoveryDecision:
    data = _decoded(raw)
    return RecoveryDecision(str(data.get("action", "none")), str(data.get("candidate_id", "")), str(data.get("reason", "")))


def _decoded(raw: str) -> dict:
    return _unwrap(json.loads(_extract_json(raw)))


def _extract_json(raw: str) -> str:
    text = raw.strip()
    return text.split("```")[1].lstrip("json").strip() if "```" in text else text


def _unwrap(data: dict | list) -> dict:
    item = data[0] if isinstance(data, list) else data
    return item["arguments"] if "arguments" in item else item


def _gate_result(data: dict) -> GateResult:
    kind = str(data.get("classification", "ambient"))
    text = str(data.get("cleaned_text", ""))
    return GateResult(kind in ("command", "conversation"), text, 1.0, {"classification": kind})
