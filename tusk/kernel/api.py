from tusk.kernel.schemas.kernel_response import KernelResponse

__all__ = ["KernelAPI"]


class KernelAPI:
    def __init__(self, pipeline: object, llm_registry: object, log: object) -> None:
        self._pipeline = pipeline
        self._llm_registry = llm_registry
        self._log = log

    def submit_text(self, text: str) -> KernelResponse:
        return self._pipeline.process_text_command(text)

    def submit_utterance(self, audio: bytes, sample_rate: int) -> KernelResponse:
        return self._pipeline.process_audio(audio, sample_rate)

    def get_pipeline_controller(self) -> object:
        return self._pipeline

    def get_llm_registry(self) -> object:
        return self._llm_registry
