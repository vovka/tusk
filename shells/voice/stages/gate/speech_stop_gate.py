from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.llm.llm_json import extract_json_payload
from tusk.shared.logging.interfaces.log_printer import LogPrinter

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

    def __init__(self, llm: LLMProvider, log_printer: LogPrinter | None = None) -> None:
        self._llm = llm
        self._log = log_printer

    def should_stop(self, text: str, speaking: str) -> bool:
        raw = self._complete(_PROMPT.format(speaking=speaking), text)
        data = self._parsed(raw)
        self._log_result(text, data)
        return bool(data.get("stop"))

    def _complete(self, prompt: str, text: str) -> str:
        try:
            return self._llm.complete_structured(prompt, text, "speech_stop_gate", _SCHEMA, 128)
        except Exception as exc:
            self._log_error("structured output failed", exc)
            return ""

    def _parsed(self, raw: str) -> dict[str, object]:
        try:
            return extract_json_payload(raw) if raw else {}
        except ValueError as exc:
            self._log_error("parse error", exc)
            return {}

    def _log_error(self, message: str, exc: Exception) -> None:
        if self._log is not None:
            self._log.log("SPEECHSTOP", f"{message}: {exc}", "speech-stop")

    def _log_result(self, text: str, data: dict[str, object]) -> None:
        if self._log is not None:
            self._log.log("SPEECHSTOP", f"stop={bool(data.get('stop'))} text={text!r}", "speech-stop")
