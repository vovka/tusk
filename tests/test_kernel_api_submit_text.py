import types

from tusk.kernel.api import KernelAPI
from tusk.kernel.schemas.kernel_response import KernelResponse


def test_kernel_api_submit_text_bypasses_gatekeeper() -> None:
    pipeline = types.SimpleNamespace(process_text_command=lambda text: KernelResponse(True, f"ok: {text}"))
    api = KernelAPI(pipeline, types.SimpleNamespace(), types.SimpleNamespace(log=lambda *a: None))
    assert api.submit_text("open terminal") == KernelResponse(True, "ok: open terminal")
