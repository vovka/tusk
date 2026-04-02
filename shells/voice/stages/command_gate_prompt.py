__all__ = ["build_command_gate_prompt"]

_BASE_PROMPT = "\n".join([
    "You are the gatekeeper for a voice assistant named TUSK.",
    "Classify each utterance as command, conversation, or ambient.",
    "Wake words only show the user is addressing TUSK.",
    "Do not treat wake-word presence alone as a command.",
    "Classify by the meaning of the remaining words after removing wake words.",
    "Treat obvious desktop commands as command even without a wake word.",
    "Conversational requests like jokes, opinions, greetings, or chit-chat are conversation even with a wake word.",
    "Treat background speech, filler, and unrelated chatter as ambient.",
    'Return strict JSON only: {"classification":"command|conversation|ambient","cleaned_text":"...","reason":"..."}.',
    "For command or conversation, remove wake words like 'tusk', 'task', 'hey tusk', or 'hey task'.",
])


def build_command_gate_prompt(context: str) -> str:
    if not context:
        return _BASE_PROMPT
    return "\n".join([
        _BASE_PROMPT,
        "The user recently interacted with TUSK. Follow-up utterances may omit the wake word.",
        "Recent context:",
        context,
    ])
