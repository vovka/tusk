import json
import types

from shells.voice.command_worker import CommandWorker
from shells.voice.stages.chunked_speaker import ChunkedSpeaker
from shells.voice.stages.gate.gatekeeper import LLMGatekeeper
from tests.command_worker_support import await_condition
from tusk.shared.interrupt import InterruptToken
from tusk.shared.schemas.kernel_response import KernelResponse
from tusk.shared.schemas.utterance import Utterance


def _llm(classification: str) -> object:
    def complete_structured(prompt, text, name, schema, max_tokens):
        return json.dumps({"classification": classification, "cleaned_text": text, "intent": "Doing it", "reason": "test"})
    return types.SimpleNamespace(complete_structured=complete_structured)


def _gatekeeper(classification: str) -> LLMGatekeeper:
    log = types.SimpleNamespace(log=lambda *args: None)
    return LLMGatekeeper(_llm(classification), log)


def test_command_classification_dispatches_with_command_kind() -> None:
    dispatch = _gatekeeper("command").process(Utterance("open gedit", b"", 1.0), [])
    assert dispatch.kind == "command"
    assert dispatch.text == "open gedit"


def test_conversation_classification_keeps_conversation_kind() -> None:
    dispatch = _gatekeeper("conversation").process(Utterance("hey tusk how are you", b"", 1.0), [])
    assert dispatch.kind == "conversation"


def _worker(calls: list[tuple[str, str]]) -> CommandWorker:
    def submit(text: str, kind: str) -> KernelResponse:
        calls.append((text, kind))
        return KernelResponse(True, "")

    log = types.SimpleNamespace(log=lambda *args: None)
    speaker = ChunkedSpeaker(None, types.SimpleNamespace(play=lambda wav: None), log)
    worker = CommandWorker(submit, speaker, log, InterruptToken())
    worker.start()
    return worker


def test_worker_forwards_kind_to_kernel_submit() -> None:
    calls: list[tuple[str, str]] = []
    _worker(calls).enqueue("open gedit", "Opening gedit", "command")
    await_condition(lambda: calls == [("open gedit", "command")])


def test_recovered_dispatch_carries_command_kind() -> None:
    from shells.voice.buffered_utterance import BufferedUtterance
    from shells.voice.recovery_decision import RecoveryDecision
    from shells.voice.stages.gate.gatekeeper_support import recovered_dispatch

    candidate = BufferedUtterance("c1", Utterance("open firefox", b"", 1.0), 0.0)
    dispatch = recovered_dispatch([candidate], RecoveryDecision("recover", candidate_id="c1"))
    assert dispatch.kind == "command"
