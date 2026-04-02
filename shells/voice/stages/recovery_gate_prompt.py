from shells.voice.buffered_utterance import BufferedUtterance

__all__ = ["build_recovery_gate_prompt"]

_BASE = "\n".join([
    "You are deciding whether a recent voice utterance should recover an earlier TUSK command.",
    "Choose recover only when the current utterance clearly refers to one prior dropped candidate.",
    "Choose ambiguous when the current utterance refers to prior speech but not to exactly one candidate.",
    "Choose none when the current utterance does not plausibly refer to a prior dropped utterance.",
    'Return strict JSON only: {"action":"recover|ambiguous|none","candidate_id":"...","reason":"..."}.',
    "Only candidate IDs from the prompt are valid recovery targets.",
])


def build_recovery_gate_prompt(context: str, candidates: list[BufferedUtterance]) -> str:
    return "\n".join([_BASE, _recent(context), _choices(candidates)])


def _recent(context: str) -> str:
    return "Recent context:\n" + (context or "(none)")


def _choices(candidates: list[BufferedUtterance]) -> str:
    lines = [f"{item.id}: {item.text}" for item in candidates]
    return "\n".join(["Recovery candidates:", *lines])
