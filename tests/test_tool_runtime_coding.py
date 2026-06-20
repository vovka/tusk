import types

from tusk.kernel.full_replace_edit_strategy import FullReplaceEditStrategy
from tusk.kernel.tool_runtime import ToolRuntime


def test_coding_router_is_wired_with_full_replace_strategy() -> None:
    captured: dict[str, object] = {}
    controller = types.SimpleNamespace(
        attach_dictation_router=lambda router: None,
        attach_coding_router=lambda router: captured.__setitem__("router", router),
    )
    runtime = ToolRuntime(_registry(), types.SimpleNamespace(), _manager(), _log())
    runtime.register_tools(controller)
    assert isinstance(captured["router"]._strategy, FullReplaceEditStrategy)


def _registry() -> object:
    return types.SimpleNamespace(register=lambda tool: None)


def _manager() -> object:
    return types.SimpleNamespace(primary_desktop_source=lambda: "gnome")


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
