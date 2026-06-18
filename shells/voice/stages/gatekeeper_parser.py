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
    return _unwrap(_loaded(raw.strip()))


def _loaded(text: str) -> dict | list:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _first_json_object(text)


def _first_json_object(text: str) -> dict:
    start = text.find("{")
    while start >= 0:
        try:
            value, _ = json.JSONDecoder().raw_decode(text[start:])
            return value
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
    raise ValueError(f"no JSON object in gate response: {text[:80]!r}")


def _unwrap(data: dict | list) -> dict:
    item = data[0] if isinstance(data, list) and data else data
    if not isinstance(item, dict):
        raise ValueError("gate response is not a JSON object")
    return item["arguments"] if "arguments" in item else item


def _gate_result(data: dict) -> GateResult:
    kind = str(data.get("classification", "ambient"))
    text = str(data.get("cleaned_text", ""))
    return GateResult(kind in ("command", "conversation"), text, 1.0, {"classification": kind})
