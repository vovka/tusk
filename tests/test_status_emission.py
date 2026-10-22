import threading
import types

import pytest

from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.schemas.voice.gate_dispatch import GateDispatch
from shells.voice.pipeline import VoicePipeline
from shells.voice.voice_shell import VoiceShell
from tusk.kernel.core.kernel_api import KernelAPI
from tusk.kernel.tools.switch_model_tool import SwitchModelTool
from tusk.shared.observability.status_reporter import StatusReporter
from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.app_status import AppStatus
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.voice.utterance import Utterance


def _hub() -> tuple[StatusReporter, list]:
    published: list = []
    return StatusReporter(types.SimpleNamespace(publish=published.append)), published


def test_kernel_submit_emits_reacting_then_restores_prior_status() -> None:
    hub, published = _hub()
    hub.set_status(AppStatus.LISTENING)
    command_mode = types.SimpleNamespace(process_command=lambda text, kind="conversation": KernelResponse(True, "ok"))
    KernelAPI(command_mode, types.SimpleNamespace(), None, hub).submit("open Firefox")
    assert [s.status for s in published] == [AppStatus.LISTENING, AppStatus.REACTING, AppStatus.LISTENING]


@pytest.mark.parametrize("name,mode", [("dictation", AppMode.DICTATION), ("coding", AppMode.CODING)])
def test_start_and_stop_mode_slot_toggle_app_mode(name: str, mode: AppMode) -> None:
    hub, _ = _hub()
    slot = getattr(KernelAPI(types.SimpleNamespace(process_command=lambda t, kind="conversation": None), types.SimpleNamespace(), None, hub), name)
    slot.start(types.SimpleNamespace())
    assert hub.status == AppStatus.STARTING and hub._snapshot().mode == mode
    slot.stop()
    assert hub._snapshot().mode == AppMode.DEFAULT


def test_pipeline_emits_listening_then_reacting_around_submit() -> None:
    hub, published = _hub()
    pipeline = _pipeline(hub)
    list(pipeline.run(lambda text, refrain="", kind="conversation": KernelResponse(True, "done")))
    assert [s.status for s in published] == [AppStatus.LISTENING, AppStatus.REACTING, AppStatus.LISTENING]


def test_voice_shell_pause_and_resume_gate_capture_and_report() -> None:
    statuses: list = []
    reporter = types.SimpleNamespace(set_status=lambda status: statuses.append(status))
    shell = VoiceShell(_config(), _log(), pipeline=types.SimpleNamespace(run=lambda submit: []), reporter=reporter)
    shell.pause()
    assert not shell._pause_gate.is_set() and statuses == [AppStatus.PAUSED]
    shell.resume()
    assert shell._pause_gate.is_set() and statuses == [AppStatus.PAUSED, AppStatus.LISTENING]


def test_switch_model_reports_updated_labels_on_success() -> None:
    reported: list = []
    registry = types.SimpleNamespace(swap=lambda *a: "swapped", model_labels=lambda: (("gatekeeper", "groq/x"),))
    SwitchModelTool(registry, types.SimpleNamespace(set_models=reported.append)).execute(_swap_params())
    assert reported == [(("gatekeeper", "groq/x"),)]


def test_switch_model_does_not_report_on_failure() -> None:
    reported: list = []
    registry = types.SimpleNamespace(swap=_raise_value_error, model_labels=lambda: ())
    SwitchModelTool(registry, types.SimpleNamespace(set_models=reported.append)).execute(_swap_params())
    assert reported == []


def _pipeline(hub: StatusReporter) -> VoicePipeline:
    detector = types.SimpleNamespace(stream_utterances=lambda: iter([Utterance("", b"a", 1.0)]))
    return VoicePipeline(detector, _transcriber(), _passthrough(), _buffer(), _gatekeeper(), reporter=hub)


def _transcriber() -> object:
    return types.SimpleNamespace(process=lambda utterance: Utterance("open Firefox", b"a", 1.0))


def _passthrough() -> object:
    return types.SimpleNamespace(process=lambda utterance: utterance)


def _buffer() -> object:
    entry = BufferedUtterance("u1", Utterance("open Firefox", b"", 1.0), 1.0)
    return types.SimpleNamespace(process=lambda u: entry, recent=lambda count: [], recoverable=lambda count, window: [], mark=lambda entry_id, state: None)


def _gatekeeper() -> object:
    return types.SimpleNamespace(process=lambda utterance, recent, candidates=None: GateDispatch("forward_current", "open Firefox"))


def _config() -> object:
    return types.SimpleNamespace(audio_sample_rate=16000, audio_frame_duration_ms=30, vad_aggressiveness=2, vad_silence_ms=400)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)


def _swap_params() -> dict:
    return {"slot": "gatekeeper", "provider": "groq", "model": "x"}


def _raise_value_error(*args: object) -> object:
    raise ValueError("bad slot")


def test_concurrent_kernel_submits_are_serialized() -> None:
    hub, published = _hub()
    hub.set_status(AppStatus.LISTENING)
    _submit_concurrently(KernelAPI(_BlockingCommandMode(), types.SimpleNamespace(), None, hub))
    assert hub.status == AppStatus.LISTENING
    expected = [AppStatus.LISTENING, AppStatus.REACTING, AppStatus.LISTENING, AppStatus.REACTING, AppStatus.LISTENING]
    assert [s.status for s in published] == expected


def _submit_concurrently(api: KernelAPI) -> None:
    command_mode = api._command_mode
    first = threading.Thread(target=lambda: api.submit("first"))
    first.start()
    command_mode.started.wait(1)
    api.submit("second")
    command_mode.release.set()
    first.join(1)


class _BlockingCommandMode:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def process_command(self, text: str, kind: str = "conversation") -> KernelResponse:
        self.calls += 1
        if text == "first":
            self.started.set()
            self.release.wait(1)
        return KernelResponse(True, text)
