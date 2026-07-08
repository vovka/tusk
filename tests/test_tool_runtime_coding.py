import types

from tusk.kernel.modes.edit_strategies.full_replace_edit_strategy import FullReplaceEditStrategy
from tusk.kernel.modes.edit_strategies.line_anchored_edit_strategy import LineAnchoredEditStrategy
from tusk.kernel.modes.edit_strategies.verified_edit_strategy import VerifiedEditStrategy
from tusk.kernel.tools.tool_runtime import ToolRuntime


def test_coding_router_is_wired_with_verified_line_anchored_strategy() -> None:
    strategy = _wired_strategy()
    assert isinstance(strategy, VerifiedEditStrategy)
    assert isinstance(strategy._primary, LineAnchoredEditStrategy)
    assert isinstance(strategy._fallback, FullReplaceEditStrategy)


def _wired_strategy() -> object:
    captured: dict[str, object] = {}
    controller = types.SimpleNamespace(
        attach_dictation_router=lambda router: None,
        attach_coding_router=lambda router: captured.__setitem__("router", router),
    )
    runtime = ToolRuntime(_registry(), types.SimpleNamespace(), _manager(), _log())
    runtime.register_tools(controller)
    return captured["router"]._strategy


def _registry() -> object:
    return types.SimpleNamespace(register=lambda tool: None)


def _manager() -> object:
    return types.SimpleNamespace(primary_desktop_source=lambda: "gnome")


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
