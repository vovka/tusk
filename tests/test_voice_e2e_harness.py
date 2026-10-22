import types

from e2e.voice_e2e_harness import VoiceE2EHarness
from tusk.shared.interrupt_token import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse


def test_empty_reply_is_not_recorded() -> None:
    harness = _harness("")
    harness._submit("hello", "conversation")
    assert harness.replies == []


def test_spoken_reply_is_recorded() -> None:
    harness = _harness("I am fine.")
    harness._submit("how are you", "conversation")
    assert harness.replies == ["I am fine."]


def test_forwarded_command_is_counted_even_when_the_worker_drops_it() -> None:
    harness = _harness("ok")
    harness._enqueue("open firefox", "", "command")
    harness._enqueue("open firefox", "", "command")
    assert harness.enqueued == ["open firefox", "open firefox"]


def _harness(reply: str) -> VoiceE2EHarness:
    kernel = types.SimpleNamespace(
        llm_registry=types.SimpleNamespace(get=lambda name: None),
        submit=lambda text, kind: KernelResponse(True, reply),
    )
    return VoiceE2EHarness(kernel, InterruptToken(), types.SimpleNamespace(log=lambda *args: None))
