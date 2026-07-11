import types

from tusk.kernel.core.kernel_api import KernelAPI
from tusk.shared.interrupt import InterruptToken


def test_request_interrupt_sets_token() -> None:
    token = InterruptToken()
    kernel = _kernel(token)
    kernel.request_interrupt()
    assert token.is_interrupted


def test_request_interrupt_without_token_is_noop() -> None:
    _kernel(None).request_interrupt()


def test_interrupt_token_is_exposed() -> None:
    token = InterruptToken()
    assert _kernel(token).interrupt_token is token


def _kernel(token: InterruptToken | None) -> KernelAPI:
    command_mode = types.SimpleNamespace(process_command=lambda text, kind="conversation": None)
    return KernelAPI(command_mode, llm_registry=None, interrupt_token=token)
