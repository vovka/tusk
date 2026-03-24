import types

from tusk.core.llm_registry import LLMRegistry
from tusk.gnome.tools.close_window_tool import CloseWindowTool
from tusk.gnome.tools.focus_window_tool import FocusWindowTool
from tusk.gnome.tools.maximize_window_tool import MaximizeWindowTool
from tusk.gnome.tools.minimize_window_tool import MinimizeWindowTool
from tusk.gnome.tools.mouse_click_tool import MouseClickTool
from tusk.gnome.tools.mouse_drag_tool import MouseDragTool
from tusk.gnome.tools.mouse_move_tool import MouseMoveTool
from tusk.gnome.tools.mouse_scroll_tool import MouseScrollTool
from tusk.gnome.tools.move_resize_window_tool import MoveResizeWindowTool
from tusk.gnome.tools.open_uri_tool import OpenUriTool
from tusk.gnome.tools.press_keys_tool import PressKeysTool
from tusk.gnome.tools.read_clipboard_tool import ReadClipboardTool
from tusk.gnome.tools.switch_workspace_tool import SwitchWorkspaceTool
from tusk.gnome.tools.type_text_tool import TypeTextTool
from tusk.gnome.tools.write_clipboard_tool import WriteClipboardTool


def test_window_and_desktop_tools(monkeypatch) -> None:
    monkeypatch.setattr("subprocess.run", lambda *a, **k: types.SimpleNamespace(stdout="99\n"))
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: None)
    assert CloseWindowTool().execute({"window_title": "a"}).success
    assert FocusWindowTool().execute({"window_title": "a"}).success
    assert MaximizeWindowTool().execute({"window_title": "a"}).success
    assert MinimizeWindowTool().execute({"window_title": "a"}).success
    assert MoveResizeWindowTool().execute({"window_title": "a", "geometry": "1,2,3,4"}).success
    assert OpenUriTool().execute({"uri": "https://example.com"}).success
    assert SwitchWorkspaceTool().execute({"workspace_number": "2"}).success


def test_input_and_clipboard_tools() -> None:
    sim = types.SimpleNamespace(press_keys=lambda *a: None, type_text=lambda *a: None, mouse_click=lambda *a: None, mouse_move=lambda *a: None, mouse_drag=lambda *a, **k: None, mouse_scroll=lambda *a: None)
    clip = types.SimpleNamespace(read=lambda: "text", write=lambda t: setattr(clip, "w", t))
    assert PressKeysTool(sim).execute({"keys": "ctrl+c"}).success
    assert TypeTextTool(sim).execute({"text": "hello"}).success
    assert MouseClickTool(sim).execute({"x": "1", "y": "2"}).success
    assert MouseMoveTool(sim).execute({"x": "1", "y": "2"}).success
    assert MouseDragTool(sim).execute({"from_x": "1", "from_y": "2", "to_x": "3", "to_y": "4"}).success
    assert MouseScrollTool(sim).execute({"direction": "up", "clicks": "1"}).success
    assert ReadClipboardTool(clip).execute({}).success
    assert WriteClipboardTool(clip).execute({"text": "x"}).success


def test_read_clipboard_empty_and_minimize_not_found(monkeypatch) -> None:
    clip = types.SimpleNamespace(read=lambda: "")
    miss = ReadClipboardTool(clip).execute({})
    monkeypatch.setattr("subprocess.run", lambda *a, **k: types.SimpleNamespace(stdout=""))
    not_found = MinimizeWindowTool().execute({"window_title": "x"})
    assert not miss.success and not not_found.success
