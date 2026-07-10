import types

from tusk.kernel.core.kernel_api import KernelAPI
from tusk.kernel.modes.coding_gate_prompt import CODING_GATE_PROMPT
from tusk.kernel.modes.dictation_gate_prompt import DICTATION_GATE_PROMPT
from tusk.kernel.modes.mode_gate import ModeGate


class RecordingLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def complete_structured(self, system_prompt: str, text: str, schema_name: str, schema: dict, max_tokens: int) -> str:
        self.prompts.append(system_prompt)
        return '{"directed": false, "cleaned_command": "", "metadata_stop": null}'


def _registry(llm: RecordingLLM, requested: list[str]) -> types.SimpleNamespace:
    def get(name: str) -> RecordingLLM:
        requested.append(name)
        return llm
    return types.SimpleNamespace(get=get)


def _kernel(llm: RecordingLLM, requested: list[str]) -> KernelAPI:
    return KernelAPI(types.SimpleNamespace(), _registry(llm, requested))


def test_dictation_gate_uses_gatekeeper_slot_and_dictation_prompt() -> None:
    llm, requested = RecordingLLM(), []
    gate = _kernel(llm, requested).dictation_gate()
    assert isinstance(gate, ModeGate)
    assert gate.should_stop("any text") is False
    assert requested == ["gatekeeper"]
    assert llm.prompts == [DICTATION_GATE_PROMPT]


def test_coding_gate_uses_gatekeeper_slot_and_coding_prompt() -> None:
    llm, requested = RecordingLLM(), []
    gate = _kernel(llm, requested).coding_gate()
    assert isinstance(gate, ModeGate)
    assert gate.should_stop("any text") is False
    assert requested == ["gatekeeper"]
    assert llm.prompts == [CODING_GATE_PROMPT]


def test_dictation_gate_does_not_crash_without_llm_registry() -> None:
    kernel = KernelAPI(types.SimpleNamespace(), None)
    assert isinstance(kernel.dictation_gate(), ModeGate)
