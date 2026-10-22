import types

from tusk.kernel.modes.editor.edit_applier import EditApplier
from tusk.kernel.modes.editor.editor_driver import EditorDriver
from tusk.kernel.tools.kernel_tool_installer import KernelToolInstaller


def test_coding_mode_is_installed_with_edit_applier_over_editor_driver() -> None:
    mode = _installed_coding_mode()
    assert isinstance(mode._applier, EditApplier)
    assert isinstance(mode._driver, EditorDriver)


def _installed_coding_mode() -> object:
    captured: dict[str, object] = {}
    kernel = types.SimpleNamespace(
        dictation=types.SimpleNamespace(attach_mode=lambda mode: None),
        coding=types.SimpleNamespace(attach_mode=lambda mode: captured.__setitem__("mode", mode)),
    )
    installer = KernelToolInstaller(_registry(), types.SimpleNamespace(), _manager(), _log())
    installer.install(kernel)
    return captured["mode"]


def _registry() -> object:
    return types.SimpleNamespace(register=lambda tool: None)


def _manager() -> object:
    return types.SimpleNamespace(primary_desktop_source=lambda: "gnome")


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
