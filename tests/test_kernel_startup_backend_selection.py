import types

import main
from tests.recording_backend import RecordingBackend
from tusk.shared.schemas.kernel_response import KernelResponse


class RuntimeStub:
    registrations: list[object] = []

    def __init__(self, *args: object) -> None:
        self._args = args

    def register_tools(self, kernel: object) -> None:
        self.registrations.append(kernel)


class FactoryStub:
    instances: list["FactoryStub"] = []

    def __init__(self, agent: object, config: object, log: object) -> None:
        self.agent = agent
        self.config = config
        self.log = log
        self.backend = RecordingBackend()
        self.instances.append(self)

    def create(self) -> RecordingBackend:
        return self.backend


def test_kernel_startup_submits_text_through_selected_backend(monkeypatch: object) -> None:
    agent = types.SimpleNamespace(name="main-agent")
    config = types.SimpleNamespace(agent_backend="codex_exec")
    monkeypatch.setattr(main, "AgentBackendFactory", FactoryStub)
    monkeypatch.setattr(main, "ToolRuntime", RuntimeStub)
    monkeypatch.setattr(main, "_build_llm_registry", lambda *args: types.SimpleNamespace(get=lambda name: object()))
    monkeypatch.setattr(main, "_build_adapter_manager", lambda *args: object())
    monkeypatch.setattr(main, "_build_agent", lambda *args: agent)
    kernel = main._build_kernel(config, types.SimpleNamespace(log=lambda *args: None), types.SimpleNamespace())
    assert kernel.submit("open browser") == KernelResponse(True, "Done.")
    assert FactoryStub.instances[0].agent is agent
    assert FactoryStub.instances[0].config is config
    assert FactoryStub.instances[0].backend.requests[0].user_text == "open browser"
