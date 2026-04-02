from shells.voice.buffered_utterance import BufferedUtterance
from shells.voice.gate_dispatch import GateDispatch
from shells.voice.recovery_decision import RecoveryDecision
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.gate_result import GateResult
from tusk.shared.schemas.utterance import Utterance

__all__ = [
    "PRIMARY_SCHEMA",
    "RECOVERY_SCHEMA",
    "fallback_dispatch",
    "has_wake_word",
    "log_gate_result",
    "log_recovery",
    "normalize_recovery",
    "recovered_dispatch",
    "to_utterance",
]

PRIMARY_SCHEMA = {
    "type": "object",
    "properties": {"classification": {"type": "string", "enum": ["command", "conversation", "ambient"]}, "cleaned_text": {"type": "string"}, "reason": {"type": "string"}},
    "required": ["classification", "cleaned_text", "reason"],
    "additionalProperties": False,
}
RECOVERY_SCHEMA = {
    "type": "object",
    "properties": {"action": {"type": "string", "enum": ["recover", "ambiguous", "none"]}, "candidate_id": {"type": "string"}, "reason": {"type": "string"}},
    "required": ["action", "candidate_id", "reason"],
    "additionalProperties": False,
}


def to_utterance(item: Utterance | BufferedUtterance) -> Utterance:
    return item if isinstance(item, Utterance) else item.utterance


def recovered_dispatch(candidates: list[BufferedUtterance], decision: RecoveryDecision) -> GateDispatch:
    item = next(candidate for candidate in candidates if candidate.id == decision.candidate_id)
    return GateDispatch("forward_recovered", item.text, item.id)


def fallback_dispatch(result: GateResult, utterance: Utterance, wake_word: bool) -> GateDispatch:
    if result.metadata.get("classification") == "conversation" and wake_word:
        return GateDispatch("forward_current", result.cleaned_command or utterance.text)
    return GateDispatch("drop")


def has_wake_word(text: str) -> bool:
    words = {part.strip(".,!?") for part in text.casefold().split()}
    return bool(words & {"tusk", "task"})


def log_gate_result(log: LogPrinter, result: GateResult, reason: str) -> None:
    kind = result.metadata.get("classification", "ambient")
    text = result.cleaned_command
    log.log("GATEKEEPER", f"classification={kind} directed={result.is_directed_at_tusk} text={text!r} reason={reason!r}", "gatekeeper")


def log_recovery(log: LogPrinter, decision: RecoveryDecision) -> None:
    msg = f"action={decision.action} candidate_id={decision.candidate_id!r} reason={decision.reason!r}"
    log.log("GATERECOVERY", msg, "gate-recovery")


def normalize_recovery(decision: RecoveryDecision, candidates: list[BufferedUtterance]) -> RecoveryDecision:
    valid = {item.id for item in candidates}
    return decision if decision.candidate_id in valid or decision.action != "recover" else RecoveryDecision("none", reason="invalid candidate")
