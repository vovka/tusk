from tusk.config import Config
from tusk.core.agent import MainAgent
from tusk.core.utterance_detector import UtteranceDetector
from tusk.interfaces.action_executor import ActionExecutor
from tusk.interfaces.gatekeeper import Gatekeeper
from tusk.interfaces.stt_engine import STTEngine
from tusk.schemas.utterance import Utterance

__all__ = ["Pipeline"]


class Pipeline:
    def __init__(
        self,
        utterance_detector: UtteranceDetector,
        stt_engine: STTEngine,
        gatekeeper: Gatekeeper,
        main_agent: MainAgent,
        action_executor: ActionExecutor,
        config: Config,
    ) -> None:
        self._detector = utterance_detector
        self._stt = stt_engine
        self._gatekeeper = gatekeeper
        self._agent = main_agent
        self._executor = action_executor
        self._config = config

    def run(self) -> None:
        print("TUSK listening...")
        for utterance in self._detector.stream_utterances():
            try:
                self._process_utterance(utterance)
            except Exception as e:
                print(f"[ERROR] {e}")

    def _process_utterance(self, utterance: Utterance) -> None:
        transcribed = self._stt.transcribe(utterance.audio_frames, self._config.audio_sample_rate)
        print(f"[STT] {transcribed.text!r} (confidence={transcribed.confidence:.2f})")
        if transcribed.confidence < 0.01:
            print("[STT] low confidence, discarded")
            return
        gate = self._gatekeeper.evaluate(transcribed)
        if not gate.is_directed_at_tusk:
            print("[GATE] discarded")
            return
        print(f"[GATE] command: {gate.cleaned_command!r}")
        action = self._agent.process_command(gate.cleaned_command)
        print(f"[AGENT] action: {action}")
        self._executor.execute(action)
