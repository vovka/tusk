import types

from tusk.kernel.api import KernelAPI
from tusk.shared.schemas.kernel_response import KernelResponse


def test_kernel_api_submit_routes_text_to_command_mode() -> None:
    command_mode = types.SimpleNamespace(process_command=lambda text: KernelResponse(True, f"ok: {text}"))
    api = KernelAPI(command_mode, types.SimpleNamespace())
    assert api.submit("open terminal") == KernelResponse(True, "ok: open terminal")
