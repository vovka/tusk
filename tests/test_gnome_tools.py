import types

from tusk.core.llm_registry import LLMRegistry
from tusk.core.tool_registry import ToolRegistry
from tusk.gnome.tool_factory import build_tool_registry
from tusk.gnome.tools.ai_transform_tool import AiTransformTool
from tusk.gnome.tools.dictation_tool import DictationTool
from tusk.gnome.tools.launch_application_tool import LaunchApplicationTool
from tusk.gnome.tools.minimize_window_tool import MinimizeWindowTool
from tusk.gnome.tools.switch_model_tool import SwitchModelTool


def test_ai_transform_tool() -> None:
    sim = types.SimpleNamespace(press_keys=lambda k: None, type_text=lambda t: setattr(sim, "typed", t))
    clip = types.SimpleNamespace(read=lambda: "text")
    llm = types.SimpleNamespace(complete=lambda *a, **k: "new")
    result = AiTransformTool(sim, clip, llm).execute({"instruction": "rewrite"})
    assert result.success and sim.typed == "new"


def test_launch_tool_and_minimize(monkeypatch) -> None:
    class Sock:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def connect(self, path): self.path = path
        def sendall(self, data): self.data = data
        def recv(self, n): return b"ok\n"
    monkeypatch.setattr("socket.socket", lambda *a: Sock())
    ok = LaunchApplicationTool("/tmp/sock").execute({"application_name": "firefox"})
    monkeypatch.setattr("subprocess.run", lambda *a, **k: types.SimpleNamespace(stdout="42\n"))
    m = MinimizeWindowTool().execute({"window_title": "x"})
    assert ok.success and m.success


def test_switch_model_and_dictation_tool() -> None:
    factory = types.SimpleNamespace(create=lambda *a: types.SimpleNamespace(label="l", complete=lambda *x: "", complete_messages=lambda *x: ""))
    reg = LLMRegistry(factory)
    reg.register_slot("agent", types.SimpleNamespace(swap=lambda provider: None))
    assert SwitchModelTool(reg).execute({"slot": "agent", "provider": "groq", "model": "m"}).success
    c = types.SimpleNamespace(set_mode=lambda mode: setattr(c, "mode", mode))
    d = DictationTool(c, types.SimpleNamespace(), types.SimpleNamespace(), lambda: "cmd", types.SimpleNamespace())
    assert d.execute({}).success and c.mode


def test_tool_factory_contains_expected_tools() -> None:
    llm = types.SimpleNamespace(label="x", complete=lambda *a: "", complete_messages=lambda *a: "")
    factory = types.SimpleNamespace(create=lambda *a: llm)
    reg = LLMRegistry(factory)
    for slot in ["utility", "gatekeeper", "agent"]: reg.register_slot(slot, types.SimpleNamespace())
    tools = build_tool_registry(types.SimpleNamespace(), types.SimpleNamespace(), llm, reg).all_tools()
    assert len(tools) >= 10


def test_remaining_tools_execute(monkeypatch) -> None:
    monkeypatch.setattr("subprocess.run", lambda *a, **k: types.SimpleNamespace(stdout=""))
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: None)
    sim = types.SimpleNamespace(press_keys=lambda *a: None, type_text=lambda *a: None, mouse_click=lambda *a: None, mouse_move=lambda *a: None, mouse_drag=lambda *a, **k: None, mouse_scroll=lambda *a: None)
    clip = types.SimpleNamespace(read=lambda: "x", write=lambda t: None)
    llm = types.SimpleNamespace(label="x", complete=lambda *a, **k: "x", complete_messages=lambda *a, **k: "x")
    reg = LLMRegistry(types.SimpleNamespace(create=lambda *a: llm))
    for slot in ["utility", "gatekeeper", "agent"]: reg.register_slot(slot, types.SimpleNamespace())
    assert build_tool_registry(sim, clip, llm, reg).all_tools()
