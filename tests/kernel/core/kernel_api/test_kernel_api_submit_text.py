import types

from tusk.kernel.core.kernel_api import KernelAPI
from tusk.shared.schemas.kernel_response import KernelResponse


def test_kernel_api_submit_routes_text_to_command_mode() -> None:
    command_mode = types.SimpleNamespace(process_command=lambda text, kind="conversation": KernelResponse(True, f"ok: {text}"))
    api = KernelAPI(command_mode, types.SimpleNamespace())
    assert api.submit("open terminal") == KernelResponse(True, "ok: open terminal")


def test_kernel_api_submit_forwards_kind_to_command_mode() -> None:
    calls: list[tuple[str, str]] = []

    def process_command(text: str, kind: str = "conversation") -> KernelResponse:
        calls.append((text, kind))
        return KernelResponse(True, "")

    api = KernelAPI(types.SimpleNamespace(process_command=process_command), types.SimpleNamespace())
    api.submit("open terminal", "command")
    api.submit("hello there")
    assert calls == [("open terminal", "command"), ("hello there", "conversation")]


def test_kernel_api_logs_input_text() -> None:
    logs: list[tuple[str, str, str]] = []
    command_mode = types.SimpleNamespace(process_command=lambda text, kind="conversation": KernelResponse(True, f"ok: {text}"))
    api = KernelAPI(command_mode, types.SimpleNamespace(), types.SimpleNamespace(log=lambda *args: logs.append(args)))
    api.submit("open terminal")
    assert logs == [("KERNELINPUT", "text='open terminal'", "kernel-input")]
