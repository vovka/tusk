# ponytail: source for the committed tray PNGs. Regenerate inside Docker:
# docker compose run --rm tusk python tools/icon_generator.py
from pathlib import Path

from PIL import Image, ImageDraw

__all__ = ["IconGenerator"]

PALETTES = {
    "light": {
        "neutral": (88, 90, 96),
        "active": (38, 166, 91),
        "busy": (224, 152, 30),
        "muted": (140, 142, 148),
        "error": (208, 64, 52),
    },
    "dark": {
        "neutral": (208, 210, 216),
        "active": (74, 214, 130),
        "busy": (245, 192, 76),
        "muted": (150, 152, 158),
        "error": (240, 112, 102),
    },
}


class IconGenerator:
    NAMES = ("neutral", "active", "busy", "muted", "error")

    def __init__(self, base_dir: str = "shells/tray/icons", scale: int = 8) -> None:
        self._base_dir = Path(base_dir)
        self._size = 22 * scale

    def generate_all(self) -> None:
        for theme, palette in PALETTES.items():
            for name in self.NAMES:
                self._render(theme, name, palette[name] + (255,))

    def _render(self, theme: str, name: str, color: tuple) -> None:
        image = Image.new("RGBA", (self._size, self._size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        self._draw_mic(draw, color)
        if name == "muted":
            self._draw_slash(draw, color)
        scaled = image.resize((22, 22), Image.Resampling.LANCZOS)
        scaled.save(self._base_dir / theme / f"{name}.png")

    def _draw_mic(self, draw: ImageDraw.ImageDraw, color: tuple) -> None:
        draw.rounded_rectangle(self._box(0.36, 0.12, 0.64, 0.52), radius=self._f(0.14), fill=color)
        draw.arc(self._box(0.27, 0.30, 0.73, 0.66), start=12, end=168, fill=color, width=self._f(0.07))
        self._draw_stand(draw, color)

    def _draw_stand(self, draw: ImageDraw.ImageDraw, color: tuple) -> None:
        width = self._f(0.07)
        draw.line((self._f(0.5), self._f(0.62), self._f(0.5), self._f(0.82)), fill=color, width=width)
        draw.line((self._f(0.38), self._f(0.82), self._f(0.62), self._f(0.82)), fill=color, width=width)

    def _draw_slash(self, draw: ImageDraw.ImageDraw, color: tuple) -> None:
        ends = (self._f(0.20), self._f(0.18), self._f(0.80), self._f(0.84))
        draw.line(ends, fill=color, width=self._f(0.11))

    def _box(self, *fracs: float) -> tuple:
        return tuple(self._f(frac) for frac in fracs)

    def _f(self, frac: float) -> int:
        return round(frac * self._size)


if __name__ == "__main__":
    IconGenerator().generate_all()
