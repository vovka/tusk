from shells.voice.buffered_utterance import BufferedUtterance

__all__ = ["build_recovery_gate_prompt"]

_BASE = "\n".join([
    "You are deciding whether a recent voice utterance should recover an earlier TUSK command.",
    "Choose recover only when the current utterance clearly refers to one prior dropped candidate.",
    "Choose ambiguous when the current utterance refers to prior speech but not to exactly one candidate.",
    "Choose none when the current utterance does not plausibly refer to a prior dropped utterance.",
    "Treat common STT wake-word variants like 'tusk', 'task', 'tasc', 'tusc', and 'dusk' as the same intended assistant address when the surrounding wording fits.",
    'Return strict JSON only: {"action":"recover|ambiguous|none","candidate_id":"...","reason":"..."}.',
    "Only candidate IDs from the prompt are valid recovery targets.",
])


def build_recovery_gate_prompt(context: str, candidates: list[BufferedUtterance]) -> str:
    return "\n".join([_BASE, _recent(context), _choices(candidates)])


def _recent(context: str) -> str:
    return "Recent context:\n" + (context or "(none)")


def _choices(candidates: list[BufferedUtterance]) -> str:
    lines = [_line(item) for item in candidates]
    return "\n".join(["Recovery candidates:", *lines])


def _line(item: BufferedUtterance) -> str:
    text = item.text
    normalized = _normalize(text)
    return f"{item.id}: {text}" if normalized == text else f"{item.id}: {text} | normalized: {normalized}"


def _normalize(text: str) -> str:
    words = [part.strip(".,!?").casefold() for part in text.split()]
    normalized = ["tusk" if part in {"task", "tasc", "tusc", "dusk"} else part for part in words]
    return " ".join(normalized)
