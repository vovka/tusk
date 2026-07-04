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
    'Return strict JSON only: {"classification":"command|conversation|ambient|interrupt","cleaned_text":"...","reason":"..."}.',
    "For command or conversation, remove wake words like 'tusk', 'task', 'hey tusk', or 'hey task'.",
])


def build_command_gate_prompt(context: str, is_busy: bool = False, speech_text: str | None = None) -> str:
    parts = [_BASE_PROMPT]
    if is_busy:
        parts.append(_busy_context())
    if speech_text is not None:
        parts.append(_speech_context(speech_text))
    if context:
        parts.extend(_recent_context(context))
    return "\n".join(parts)


def _busy_context() -> str:
    return "TUSK is currently busy executing a task. If the utterance expresses intent to stop / cancel / abort the current activity in any wording, classify it as `interrupt`."


def _speech_context(speech_text: str) -> str:
    return f"TUSK is currently saying aloud: '{speech_text}'. Utterances that repeat or echo fragments of it are TUSK's own voice; classify them as ambient."


def _recent_context(context: str) -> list[str]:
    return [
        "The user recently interacted with TUSK. Follow-up utterances may omit the wake word.",
        "Recent context:",
        context,
    ]
