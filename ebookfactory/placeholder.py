"""Procedural placeholder illustrations (PIL only) so a fresh book builds with images."""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

PALETTES = [
    ((250, 236, 214), (214, 160, 104), (120, 72, 40)),   # crust
    ((236, 242, 230), (150, 180, 130), (60, 90, 50)),    # sage
    ((240, 232, 246), (170, 140, 200), (80, 60, 110)),   # lavender
    ((230, 240, 248), (120, 160, 200), (40, 70, 110)),   # sky
]


def _font(size: int):
    for f in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient(w, h, top, bottom):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return im


def _jar(d, cx, cy, s, ink, light):
    w, h = s * 0.55, s * 0.8
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=s * 0.08, fill=(255, 255, 255, 150), outline=ink, width=int(s * .02))
    d.rounded_rectangle([cx - w / 2 + s * .03, cy - h * .05, cx + w / 2 - s * .03, cy + h / 2 - s * .03], radius=s * .05, fill=light)
    for i in range(14):  # bubbles
        bx, by = cx + random.uniform(-w / 2.6, w / 2.6), cy + random.uniform(0, h / 2.4)
        r = random.uniform(s * .008, s * .025)
        d.ellipse([bx - r, by - r, bx + r, by + r], outline=ink, width=2)
    d.rectangle([cx - w / 2 - s * .03, cy - h / 2 - s * .07, cx + w / 2 + s * .03, cy - h / 2 + s * .01], fill=ink)


def _loaf(d, cx, cy, s, ink, light):
    w, h = s * 0.95, s * 0.55
    d.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=light, outline=ink, width=int(s * .02))
    for i in range(-2, 3):  # scoring
        x = cx + i * w * 0.15
        d.arc([x - w * .12, cy - h * .38, x + w * .12, cy + h * .1], 200, 340, fill=ink, width=int(s * .018))


def _bowl(d, cx, cy, s, ink, light):
    w = s * 0.9
    d.pieslice([cx - w / 2, cy - w / 2.4, cx + w / 2, cy + w / 2.4], 0, 180, fill=light, outline=ink, width=int(s * .02))
    d.ellipse([cx - w / 2.4, cy - s * .12, cx + w / 2.4, cy + s * .06], fill=(255, 250, 240), outline=ink, width=int(s * .012))


def _wheat(d, cx, cy, s, ink, light):
    for k in (-1, 0, 1):
        x0 = cx + k * s * .18
        d.line([(x0, cy + s * .45), (x0 + k * s * .06, cy - s * .35)], fill=ink, width=int(s * .02))
        for j in range(6):
            yy = cy - s * .3 + j * s * .09
            xx = x0 + k * s * .06 * (1 - j / 6)
            for side in (-1, 1):
                d.ellipse([xx + side * s * .05 - s * .035, yy - s * .02, xx + side * s * .05 + s * .035, yy + s * .045], fill=light, outline=ink, width=2)


MOTIFS = {"jar": _jar, "loaf": _loaf, "bowl": _bowl, "wheat": _wheat}


def make_placeholder(out: Path, label: str = "", size=(1600, 1067), seed: int = 0, motif: str | None = None,
                     palette: int | None = None) -> Path:
    random.seed(seed)
    w, h = size
    bg, mid, ink = PALETTES[(palette if palette is not None else seed) % len(PALETTES)]
    im = _gradient(w, h, bg, tuple(int(c * .82) for c in mid)).convert("RGBA")
    bokeh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bokeh)
    for _ in range(26):
        r = random.uniform(.03, .14) * min(w, h)
        x, y = random.uniform(0, w), random.uniform(0, h)
        bd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, random.randint(18, 60)))
    im = Image.alpha_composite(im, bokeh.filter(ImageFilter.GaussianBlur(min(w, h) * .02)))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    s = min(w, h) * 0.62
    # table line + soft shadow
    d.rectangle([0, h * .78, w, h], fill=tuple(int(c * .75) for c in mid) + (255,))
    d.ellipse([w / 2 - s * .55, h * .74, w / 2 + s * .55, h * .82], fill=(0, 0, 0, 50))
    fn = MOTIFS.get(motif or "", None) or list(MOTIFS.values())[seed % len(MOTIFS)]
    fn(d, w / 2, h * .5, s, ink + (255,), mid + (255,))
    im = Image.alpha_composite(im, layer)
    if label:
        d2 = ImageDraw.Draw(im)
        f = _font(max(18, int(h * .035)))
        tw = d2.textlength(label, font=f)
        pad = h * .015
        d2.rounded_rectangle([w * .03, h * .04, w * .03 + tw + pad * 3, h * .04 + h * .035 + pad * 2.4], radius=pad,
                             fill=(255, 255, 255, 210))
        d2.text((w * .03 + pad * 1.5, h * .04 + pad), label, font=f, fill=ink)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(out, "JPEG", quality=90)
    return out
