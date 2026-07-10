import types

from tests.factory_stub import FactoryStub
from tusk.kernel.core import startup
from tusk.shared.schemas.kernel_response import KernelResponse


class RuntimeStub:
    registrations: list[object] = []

    def __init__(self, *args: object) -> None:
        self._args = args

    def register_tools(self, kernel: object) -> None:
        self.registrations.append(kernel)


def test_kernel_startup_submits_text_through_selected_backend(monkeypatch: object) -> None:
    FactoryStub.instances.clear()
    RuntimeStub.registrations.clear()
    agent = types.SimpleNamespace(name="main-agent")
    config = types.SimpleNamespace(agent_backend="codex_exec")
    _patch_startup(monkeypatch, agent)
    kernel = startup.build_kernel(config, _log(), _llm_registry(), None)
    assert kernel.submit("open browser") == KernelResponse(True, "Done.")
    _assert_factory_received(agent, config, "open browser")


def _patch_startup(monkeypatch: object, agent: object) -> None:
    monkeypatch.setattr(startup, "AgentBackendFactory", FactoryStub)
    monkeypatch.setattr(startup, "ToolRuntime", RuntimeStub)
    monkeypatch.setattr(startup, "build_adapter_manager", lambda *args: object())
    monkeypatch.setattr(startup, "build_agent", lambda *args: agent)


def _llm_registry() -> object:
    return types.SimpleNamespace(get=lambda name: object())


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)


def _assert_factory_received(agent: object, config: object, user_text: str) -> None:
    assert FactoryStub.instances[0].agent is agent
    assert FactoryStub.instances[0].config is config
    assert FactoryStub.instances[0].backend.requests[0].user_text == user_text
