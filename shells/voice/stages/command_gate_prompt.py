__all__ = ["build_command_gate_prompt"]

_BASE_PROMPT = "\n".join([
    "You are the gatekeeper for a voice assistant named TUSK.",
    "Classify each utterance as command, conversation, or ambient.",
    "Be conservative: if there is any meaningful doubt that the utterance is for TUSK, classify it as ambient.",
    "Wake words only show the user is addressing TUSK.",
    "Do not treat wake-word presence alone as a command.",
    "Classify by the meaning of the remaining words after removing wake words.",
    "Treat a no-wake-word utterance as command only when it is a clear direct imperative for TUSK.",
    "Conversational requests like jokes, opinions, greetings, or chit-chat are conversation even with a wake word.",
    "Without a wake word, treat chit-chat, observations, and open-ended questions as ambient unless they clearly continue a task or correct a prior drop.",
    "Treat background speech, filler, and unrelated chatter as ambient.",
    "When uncertain between command/conversation and ambient, choose ambient.",
    'Return strict JSON only: {"classification":"command|conversation|ambient","cleaned_text":"...","reason":"..."}.',
    "For command or conversation, remove wake words like 'tusk', 'task', 'hey tusk', or 'hey task'.",
])

_BUSY_CLAUSE = "\n".join([
    "TUSK is currently busy executing a task.",
    "If the utterance expresses intent to stop, cancel, abort, or dismiss the current activity — in any wording — classify it as interrupt.",
    'While TUSK is busy, "interrupt" is also a valid classification value.',
])

_SPEAKING_CLAUSE = "\n".join([
    "TUSK is currently saying aloud: {text!r}.",
    "Utterances that repeat or echo fragments of that sentence are TUSK's own voice picked up by the microphone — classify them as ambient.",
])


def build_command_gate_prompt(context: str, busy: bool = False, speaking: str | None = None) -> str:
    parts = [_BASE_PROMPT]
    if busy:
        parts.append(_BUSY_CLAUSE)
    if speaking:
        parts.append(_SPEAKING_CLAUSE.format(text=speaking))
    if context:
        parts.append(_context_clause(context))
    return "\n".join(parts)


def _context_clause(context: str) -> str:
    return "\n".join([
        "The user recently interacted with TUSK. Follow-up utterances may omit the wake word.",
        "Recent context:",
        context,
    ])
