from shells.voice.audio_capture import AudioCapture
from shells.voice.utterance_detector import UtteranceDetector
from tusk.kernel.interfaces.shell import Shell

__all__ = ["VoiceShell"]


class VoiceShell(Shell):
    def __init__(self, config: object, log_printer: object) -> None:
        self._audio = AudioCapture(config.audio_sample_rate, config.audio_frame_duration_ms)
        self._detector = UtteranceDetector(
            self._audio,
            config.audio_sample_rate,
            config.vad_aggressiveness,
            log_printer,
        )
        self._config = config
        self._log = log_printer
        self._running = True

    def start(self, api: object) -> None:
        for utterance in self._detector.stream_utterances():
            if not self._running:
                return
            result = api.submit_utterance(utterance.audio_frames, self._config.audio_sample_rate)
            self._log_reply(result)

    def stop(self) -> None:
        self._running = False

    def _log_reply(self, result: object) -> None:
        reply = getattr(result, "reply", "")
        if reply:
            self._log.log("TUSK", reply)
