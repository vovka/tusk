from shells.voice.gate.wake_words import has_wake_word
from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_action import GateAction
from tusk.shared.schemas.voice.gate_classification import GateClassification
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from tusk.shared.schemas.voice.gate_result import GateResult
from tusk.shared.schemas.voice.recovery_decision import RecoveryDecision
from tusk.shared.schemas.voice.utterance import Utterance

__all__ = ["fallback_dispatch", "recent_context", "recovered_dispatch", "recovery_worthwhile"]

_REFERENCE_CUES = frozenset({"that", "those", "this", "these", "previous", "last", "earlier", "before", "again", "instead", "actually", "meant", "one", "it", "them", "prior", "recent", "other", "no", "yes", "yeah"})
_MAX_CONTENT_LENGTH = 150


def recent_context(utterances: list[Utterance], max_utterances: int = 6) -> str:
    recent = [item for item in utterances if item.text.strip()][-max_utterances:]
    return "\n".join(f"User: {item.text[:_MAX_CONTENT_LENGTH]}" for item in recent)


def recovered_dispatch(candidates: list[BufferedUtterance], decision: RecoveryDecision) -> GateDispatch:
    item = next(candidate for candidate in candidates if candidate.id == decision.candidate_id)
    # recovery rescues a dropped desktop command, so route it through the command fast path
    return GateDispatch(GateAction.FORWARD_RECOVERED, item.text, item.id, kind="command")


def fallback_dispatch(result: GateResult, text: str, wake_word: bool) -> GateDispatch:
    if result.classification == GateClassification.CONVERSATION and wake_word:
        return GateDispatch(GateAction.FORWARD_CURRENT, result.cleaned_command or text, intent=result.intent)
    return GateDispatch(GateAction.DROP)


def recovery_worthwhile(text: str, primary: GateResult, candidates: list[BufferedUtterance]) -> bool:
    # ponytail: skip the recovery LLM call for clearly non-referential ambient chatter.
    # Ceiling: a cue-less, wake-word-less correction classified ambient is dropped, not recovered.
    if not candidates:
        return False
    if primary.classification != GateClassification.AMBIENT or has_wake_word(text):
        return True
    words = {part.strip(".,!?") for part in text.casefold().split()}
    return bool(words & _REFERENCE_CUES)
