from shells.voice.gate.llm_client import LLMClient
from tusk.shared.interfaces.log_printer import LogPrinter

__all__ = ["SpeechStopGate"]

_SCHEMA = {
    "type": "object",
    "properties": {"stop": {"type": "boolean"}, "reason": {"type": "string"}},
    "required": ["stop", "reason"],
    "additionalProperties": False,
}

_PROMPT = "\n".join([
    "TUSK, a voice assistant, is currently reading a response aloud.",
    "TUSK is saying: {speaking!r}.",
    "The microphone picked up an utterance. Return stop=true only when the utterance's sole,",
    "unambiguous meaning is that the user wants TUSK to stop, cancel, or silence what it is doing —",
    "in any wording, e.g. 'stop it', 'quit it', 'abort', \"let's not do it\", 'be quiet'.",
    "Utterances that repeat or echo fragments of TUSK's own sentence are its own voice: not a stop request.",
    "Self-talk or narration such as \"I'm going to go\" and anything ambiguous is not a stop request.",
    'Return strict JSON only: {{"stop":true|false,"reason":"..."}}.',
])


class SpeechStopGate:
    """Semantic yes/no classifier: does an utterance heard during playback ask TUSK to stop?"""

    def __init__(self, client: LLMClient, log_printer: LogPrinter) -> None:
        self._client = client
        self._log = log_printer

    def should_stop(self, text: str, speaking: str) -> bool:
        data = self._client.complete(_PROMPT.format(speaking=speaking), text, "speech_stop_gate", _SCHEMA, 128)
        stop = bool(data.get("stop"))
        self._log.log("SPEECHSTOP", f"stop={stop} text={text!r}", "speech-stop")
        return stop
