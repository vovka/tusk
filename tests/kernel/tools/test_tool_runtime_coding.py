import types

from tusk.kernel.modes.editor.edit_applier import EditApplier
from tusk.kernel.modes.editor.editor_driver import EditorDriver
from tusk.kernel.tools.tool_runtime import ToolRuntime


def test_coding_router_is_wired_with_edit_applier_over_editor_driver() -> None:
    router = _wired_router()
    assert isinstance(router._applier, EditApplier)
    assert isinstance(router._driver, EditorDriver)


def _wired_router() -> object:
    captured: dict[str, object] = {}
    controller = types.SimpleNamespace(
        dictation=types.SimpleNamespace(attach_router=lambda router: None),
        coding=types.SimpleNamespace(attach_router=lambda router: captured.__setitem__("router", router)),
    )
    runtime = ToolRuntime(_registry(), types.SimpleNamespace(), _manager(), _log())
    runtime.register_tools(controller)
    return captured["router"]


def _registry() -> object:
    return types.SimpleNamespace(register=lambda tool: None)


def _manager() -> object:
    return types.SimpleNamespace(primary_desktop_source=lambda: "gnome")


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
