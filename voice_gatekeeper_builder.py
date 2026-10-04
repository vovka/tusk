from shells.voice.command_worker import CommandWorker
from shells.voice.gatekeeper_slot import GatekeeperSlot
from shells.voice.playback_gate import PlaybackGate
from shells.voice.stages.gate.gatekeeper import LLMGatekeeper
from shells.voice.stages.gate.speech_stop_gate import SpeechStopGate
from shells.voice.stages.gate.stop_gatekeeper import StopGatekeeper

__all__ = ["VoiceGatekeeperBuilder"]


class VoiceGatekeeperBuilder:
    """Builds the voice gatekeeper slot, swapping in dictation/coding gates while those modes run."""

    def __init__(self, config: object, kernel: object, log: object) -> None:
        self._config = config
        self._kernel = kernel
        self._log = log

    def build(self, worker: CommandWorker) -> GatekeeperSlot:
        registry = self._kernel.get_llm_registry()
        gk_llm = registry.get("gatekeeper") if registry else None
        stop_llm = registry.get_with_fallback("stop_gate", "gatekeeper") if registry else None
        base = self._guarded(self._base_gate(gk_llm, worker), stop_llm, worker)
        slot = GatekeeperSlot(base)
        self._wire_modes(slot, base, stop_llm, worker)
        return slot

    def _base_gate(self, gk_llm: object, worker: CommandWorker) -> LLMGatekeeper:
        return LLMGatekeeper(
            gk_llm, self._log, follow_up_window_seconds=self._config.follow_up_timeout_seconds,
            is_busy=lambda: worker.is_busy, current_speech_text=lambda: worker.current_speech_text,
        )

    def _wire_modes(self, slot: GatekeeperSlot, base: object, stop_llm: object, worker: CommandWorker) -> None:
        self._wire_mode(slot, base, stop_llm, worker, self._kernel.dictation_gate(),
                        self._kernel.set_dictation_callbacks, self._kernel.request_dictation_stop)
        self._wire_mode(slot, base, stop_llm, worker, self._kernel.coding_gate(),
                        self._kernel.set_coding_callbacks, self._kernel.request_coding_stop)

    def _wire_mode(self, slot: GatekeeperSlot, base: object, stop_llm: object, worker: CommandWorker,
                   gate: object, set_callbacks: object, request_stop: object) -> None:
        make = lambda: self._guarded(StopGatekeeper(gate, request_stop, base), stop_llm, worker)
        set_callbacks(on_start=lambda: slot.swap(make()), on_stop=lambda: slot.swap(base))

    def _guarded(self, inner: object, stop_llm: object, worker: CommandWorker) -> PlaybackGate:
        # while TUSK's own voice plays, only stop_gate (STOP_GATE_LLM) may interrupt; otherwise delegate to inner
        return PlaybackGate(inner, lambda: worker.current_speech_text, SpeechStopGate(stop_llm, self._log))
