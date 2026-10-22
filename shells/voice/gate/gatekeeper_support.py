import string

from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_action import GateAction
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from tusk.shared.schemas.voice.recovery_decision import RecoveryDecision
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.voice.gate_classification import GateClassification
from tusk.shared.schemas.voice.gate_result import GateResult
from tusk.shared.schemas.voice.utterance import Utterance

__all__ = [
    "PRIMARY_SCHEMA",
    "RECOVERY_SCHEMA",
    "WAKE_WORDS",
    "fallback_dispatch",
    "has_wake_word",
    "starts_with_wake_word",
    "log_gate_result",
    "log_recovery",
    "normalize_recovery",
    "recovered_dispatch",
    "recovery_worthwhile",
    "to_utterance",
]

_REFERENCE_CUES = frozenset({"that", "those", "this", "these", "previous", "last", "earlier", "before", "again", "instead", "actually", "meant", "one", "it", "them", "prior", "recent", "other", "no", "yes", "yeah"})
# "task" and "dusk" are common STT mishearings of the wake word
WAKE_WORDS = frozenset({"tusk", "task", "dusk", "tosk"})

PRIMARY_SCHEMA = {
    "type": "object",
    "properties": {"classification": {"type": "string", "enum": ["command", "conversation", "ambient", "interrupt"]}, "cleaned_text": {"type": "string"}, "intent": {"type": "string"}, "reason": {"type": "string"}},
    "required": ["classification", "cleaned_text", "intent", "reason"],
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
    # recovery rescues a dropped desktop command, so route it through the command fast path
    return GateDispatch(GateAction.FORWARD_RECOVERED, item.text, item.id, kind="command")


def fallback_dispatch(result: GateResult, utterance: Utterance, wake_word: bool) -> GateDispatch:
    if result.classification == GateClassification.CONVERSATION and wake_word:
        return GateDispatch(GateAction.FORWARD_CURRENT, result.cleaned_command or utterance.text, intent=result.intent)
    return GateDispatch(GateAction.DROP)


def has_wake_word(text: str) -> bool:
    words = {part.strip(".,!?") for part in text.casefold().split()}
    return bool(words & WAKE_WORDS)


def starts_with_wake_word(text: str) -> bool:
    tokens = text.split()
    return bool(tokens) and tokens[0].strip(string.punctuation).casefold() in WAKE_WORDS


def recovery_worthwhile(utterance: Utterance, primary: GateResult, candidates: list[BufferedUtterance]) -> bool:
    # ponytail: skip the recovery LLM call for clearly non-referential ambient chatter.
    # Ceiling: a cue-less, wake-word-less correction classified ambient is dropped, not recovered.
    if not candidates:
        return False
    if primary.classification != GateClassification.AMBIENT or has_wake_word(utterance.text):
        return True
    words = {part.strip(".,!?") for part in utterance.text.casefold().split()}
    return bool(words & _REFERENCE_CUES)


def log_gate_result(log: LogPrinter, result: GateResult, reason: str) -> None:
    kind = str(result.classification)
    text = result.cleaned_command
    log.log("GATEKEEPER", f"classification={kind} directed={result.is_directed_at_tusk} text={text!r} reason={reason!r}", "gatekeeper")


def log_recovery(log: LogPrinter, decision: RecoveryDecision) -> None:
    msg = f"action={decision.action} candidate_id={decision.candidate_id!r} reason={decision.reason!r}"
    log.log("GATERECOVERY", msg, "gate-recovery")


def normalize_recovery(decision: RecoveryDecision, candidates: list[BufferedUtterance]) -> RecoveryDecision:
    valid = {item.id for item in candidates}
    return decision if decision.candidate_id in valid or decision.action != "recover" else RecoveryDecision("none", reason="invalid candidate")
