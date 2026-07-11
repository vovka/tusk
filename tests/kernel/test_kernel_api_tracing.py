import types

from tests.recording_tracer import RecordingTracer
from tusk.kernel.core.kernel_api import KernelAPI
from tusk.shared.schemas.kernel_response import KernelResponse


def _command_mode() -> object:
    return types.SimpleNamespace(process_command=lambda text: KernelResponse(True, "done"))


def test_submit_opens_root_span_with_request_id() -> None:
    tracer = RecordingTracer()
    kernel = KernelAPI(_command_mode(), None, tracer=tracer)
    kernel.submit("open gedit")
    assert tracer.spans[0]["name"] == "kernel.request"
    attributes = tracer.spans[0]["attributes"]
    assert attributes["text_preview"] == "open gedit"
    assert len(attributes["request_id"]) == 32


def test_submit_records_handled_on_the_request_span() -> None:
    tracer = RecordingTracer()
    kernel = KernelAPI(_command_mode(), None, tracer=tracer)
    kernel.submit("open gedit")
    assert tracer.spans[0]["attributes"]["handled"] == "True"


def test_submit_generates_distinct_request_ids() -> None:
    tracer = RecordingTracer()
    kernel = KernelAPI(_command_mode(), None, tracer=tracer)
    kernel.submit("first")
    kernel.submit("second")
    ids = [span["attributes"]["request_id"] for span in tracer.spans]
    assert ids[0] != ids[1]
