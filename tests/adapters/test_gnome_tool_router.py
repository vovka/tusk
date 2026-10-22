import types
from unittest.mock import Mock

import pytest

from adapters.gnome.gnome_tool_router import GnomeToolRouter


def _router(**window_collaborators: object) -> GnomeToolRouter:
    apps = types.SimpleNamespace(list_apps=lambda: [])
    return GnomeToolRouter(apps, object(), object(), object(), **window_collaborators)


def test_router_uses_the_injected_window_collaborators() -> None:
    window_tools, windows = Mock(), Mock()
    router = _router(window_tools=window_tools, windows=windows)
    assert router._handlers["focus_window"] is window_tools.focus_window
    assert router._windows is windows


def test_router_has_no_default_backend() -> None:
    with pytest.raises(TypeError):
        _router()
