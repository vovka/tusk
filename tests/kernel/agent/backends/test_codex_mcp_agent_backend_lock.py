import threading
import time
from unittest.mock import patch

from tusk.kernel.agent_backends.agent_request import AgentRequest
from tests.kernel.agent.backends.test_codex_mcp_agent_backend import _CLIENT, FakeClient, backend, success


def _warmed_client(instance: object) -> FakeClient:
    FakeClient.pending = [success()]
    instance.run(AgentRequest("warm up", "command"))
    return FakeClient.instances[0]


def _turn_threads(instance: object, count: int) -> list[threading.Thread]:
    request = AgentRequest("go", "command")
    return [threading.Thread(target=instance.run, args=(request,)) for _ in range(count)]


def _run_all(threads: list[threading.Thread]) -> None:
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def test_concurrent_turns_are_serialized_by_the_backend_lock() -> None:
    instance = backend()
    with patch(_CLIENT, FakeClient):
        client = _warmed_client(instance)
        client.responses, client.delay = [success(), success()], 0.1
        threads = _turn_threads(instance, 2)
        started = time.monotonic()
        _run_all(threads)
    assert time.monotonic() - started >= 0.2
