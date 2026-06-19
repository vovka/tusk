import importlib
import sys
from pathlib import Path

import pytest

from shells.tray.status_icon_resolver import StatusIconResolver
from tusk.shared.schemas.app_status import AppStatus

THEMES = ("light", "dark")
NAMES = ("neutral", "active", "busy", "muted", "error")


@pytest.fixture(scope="module")
def image_module() -> object:
    # conftest stubs PIL for headless logic tests; these tests inspect real
    # pixels, so swap the real Pillow in and restore the stub afterwards.
    saved = {name: sys.modules.pop(name, None) for name in ("PIL", "PIL.Image")}
    try:
        yield importlib.import_module("PIL.Image")
    finally:
        sys.modules.update({name: mod for name, mod in saved.items() if mod})


def _open(image_module: object, theme: str, name: str) -> object:
    return image_module.open(f"shells/tray/icons/{theme}/{name}.png").convert("RGBA")


def test_icons_are_22px(image_module: object) -> None:
    for theme in THEMES:
        for name in NAMES:
            assert _open(image_module, theme, name).size == (22, 22)


def test_icons_have_glyph_on_transparent_background(image_module: object) -> None:
    # Placeholders were fully opaque single-color squares; a real glyph has
    # painted pixels (alpha 255) over a transparent background (alpha 0).
    for theme in THEMES:
        for name in NAMES:
            low, high = _open(image_module, theme, name).getchannel("A").getextrema()
            assert low == 0 and high == 255


def test_states_are_visually_distinct(image_module: object) -> None:
    for theme in THEMES:
        rendered = {_open(image_module, theme, name).tobytes() for name in NAMES}
        assert len(rendered) == len(NAMES)


def test_resolver_paths_exist() -> None:
    resolver = StatusIconResolver("light")
    for status in AppStatus:
        path = resolver.resolve(status)
        if path:
            assert Path(path).exists()
