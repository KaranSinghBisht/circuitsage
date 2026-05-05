"""Generate the CircuitSage Kaggle cover image (1600x900, brand-aligned).

Run:
    backend/.venv/bin/python scripts/make_cover.py

Outputs:
    media/cover.png
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parents[1] / "media" / "cover.png"
WIDTH, HEIGHT = 1600, 900

BG = (16, 20, 18)
PANEL = (25, 32, 29)
LINE = (49, 64, 57)
TEXT = (238, 245, 235)
MUTED = (155, 173, 159)
ACCENT = (103, 242, 169)
AMBER = (255, 191, 87)
RED = (255, 95, 86)


def _font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Avenir Next.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _serif(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/System/Library/Fonts/Supplemental/Times.ttc",
        "/Library/Fonts/Times New Roman.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return _font(size)


def _radial_glow(size: tuple[int, int], color: tuple[int, int, int], intensity: float = 0.45) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, BG)
    cx, cy = width * 0.18, height * 0.0
    max_radius = math.hypot(max(cx, width - cx), max(cy, height - cy))
    pixels = image.load()
    for y in range(height):
        for x in range(0, width, 2):
            distance = math.hypot(x - cx, y - cy)
            falloff = max(0.0, 1.0 - distance / max_radius)
            mix = falloff * intensity
            pixels[x, y] = (
                int(BG[0] + (color[0] - BG[0]) * mix),
                int(BG[1] + (color[1] - BG[1]) * mix),
                int(BG[2] + (color[2] - BG[2]) * mix),
            )
            if x + 1 < width:
                pixels[x + 1, y] = pixels[x, y]
    return image.filter(ImageFilter.GaussianBlur(radius=24))


def _draw_waveform(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
    points = []
    for px in range(w):
        t = px / w
        envelope = math.sin(t * math.pi * 2.4) * 0.42
        wobble = math.sin(t * math.pi * 17) * 0.05
        py = y + h / 2 + (envelope + wobble) * h * 0.45
        points.append((x + px, py))
    for index in range(1, len(points)):
        draw.line([points[index - 1], points[index]], fill=color, width=4)


def _draw_clipped(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
    rail = y + h * 0.18
    points = []
    for px in range(w):
        t = px / w
        wobble = math.sin(t * math.pi * 22) * 0.012
        points.append((x + px, rail + wobble * h))
    for index in range(1, len(points)):
        draw.line([points[index - 1], points[index]], fill=color, width=4)
    draw.line([(x, rail), (x + w, rail)], fill=color, width=4)


def _grid(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
    step_x = w // 12
    step_y = h // 6
    for i in range(1, 12):
        draw.line([(x + i * step_x, y + 4), (x + i * step_x, y + h - 4)], fill=LINE, width=1)
    for i in range(1, 6):
        draw.line([(x + 4, y + i * step_y), (x + w - 4, y + i * step_y)], fill=LINE, width=1)


def _panel(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
    draw.rectangle([x, y, x + w, y + h], fill=PANEL, outline=LINE, width=2)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = _radial_glow((WIDTH, HEIGHT), ACCENT, intensity=0.32)
    draw = ImageDraw.Draw(canvas)

    bar_height = 6
    draw.rectangle([0, 0, WIDTH, bar_height], fill=ACCENT)

    eyebrow = _font(26, "bold")
    title = _serif(140)
    subtitle = _font(36)
    label = _font(22)
    chip = _font(24, "bold")

    draw.text((96, 110), "CIRCUITSAGE", font=eyebrow, fill=ACCENT)
    draw.text((96, 162), "Stack traces", font=title, fill=TEXT)
    draw.text((96, 304), "for circuits.", font=title, fill=TEXT)
    draw.text(
        (96, 470),
        "An offline Gemma-4-powered lab partner that turns silent",
        font=subtitle,
        fill=MUTED,
    )
    draw.text(
        (96, 514),
        "bench failures into a step-by-step debugging path.",
        font=subtitle,
        fill=MUTED,
    )

    chip_x = 96
    chip_y = 592
    for text, color in [
        ("Future of Education", ACCENT),
        ("Digital Equity", AMBER),
        ("Safety & Trust", (120, 168, 255)),
    ]:
        bbox = draw.textbbox((0, 0), text, font=chip)
        cw = bbox[2] - bbox[0] + 28
        ch = bbox[3] - bbox[1] + 18
        draw.rectangle([chip_x, chip_y, chip_x + cw, chip_y + ch], outline=color, width=2)
        draw.text((chip_x + 14, chip_y + 6), text, font=chip, fill=color)
        chip_x += cw + 14

    panel_w = 560
    panel_h = 420
    panel_x = WIDTH - panel_w - 96
    panel_y = 200
    _panel(draw, panel_x, panel_y, panel_w, panel_h)
    draw.text((panel_x + 24, panel_y + 22), "OBSERVED VS EXPECTED", font=eyebrow, fill=ACCENT)
    grid_w = panel_w - 48
    grid_h = panel_h - 110
    grid_x = panel_x + 24
    grid_y = panel_y + 70
    _grid(draw, grid_x, grid_y, grid_w, grid_h)
    _draw_waveform(draw, grid_x, grid_y, grid_w, grid_h, ACCENT)
    _draw_clipped(draw, grid_x, grid_y, grid_w, grid_h, RED)
    legend_y = panel_y + panel_h - 36
    draw.rectangle([panel_x + 24, legend_y, panel_x + 50, legend_y + 4], fill=ACCENT)
    draw.text((panel_x + 60, legend_y - 12), "expected -4.7 V peak", font=label, fill=TEXT)
    draw.rectangle([panel_x + 280, legend_y, panel_x + 306, legend_y + 4], fill=RED)
    draw.text((panel_x + 316, legend_y - 12), "observed clipped at +12 V", font=label, fill=TEXT)

    fault_y = panel_y + panel_h + 24
    draw.rectangle([panel_x, fault_y, panel_x + panel_w, fault_y + 70], fill=PANEL, outline=LINE, width=2)
    draw.text((panel_x + 24, fault_y + 12), "TOP FAULT", font=eyebrow, fill=ACCENT)
    draw.text((panel_x + 24, fault_y + 38), "Floating non-inverting input", font=label, fill=TEXT)
    draw.text((panel_x + 380, fault_y + 38), "0.86", font=label, fill=ACCENT)

    draw.text(
        (96, HEIGHT - 60),
        "Local-first  -  Function calling  -  Multimodal  -  Unsloth LoRA",
        font=label,
        fill=MUTED,
    )

    canvas.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
