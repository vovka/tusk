from collections.abc import Callable, Iterator

from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.utterance import Utterance

__all__ = ["VoicePipeline"]


class VoicePipeline:
    def __init__(
        self,
        detector: object,
        transcriber: object,
        sanitizer: object,
        buffer: object,
        gatekeeper: object,
    ) -> None:
        self._detector = detector
        self._transcriber = transcriber
        self._sanitizer = sanitizer
        self._buffer = buffer
        self._gatekeeper = gatekeeper

    def run(self, submit: Callable[[str], KernelResponse]) -> Iterator[KernelResponse]:
        for utterance in self._detector.stream_utterances():
            result = self._handle_utterance(utterance, submit)
            if result is not None:
                yield result

    def _handle_utterance(
        self,
        utterance: Utterance,
        submit: Callable[[str], KernelResponse],
    ) -> KernelResponse | None:
        transcribed = self._transcriber.process(utterance)
        sanitized = self._sanitizer.process(transcribed)
        if sanitized is None:
            return None
        buffered = self._buffer.process(sanitized)
        if buffered is None:
            return None
        command = self._gatekeeper.process(buffered, self._buffer.recent(6))
        return None if command is None else submit(command)
