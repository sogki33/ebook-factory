"""Regenerate the placeholder illustrations for the demo book (PIL only)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebookfactory.placeholder import make_placeholder  # noqa: E402

IMG = Path(__file__).resolve().parents[1] / "examples" / "sourdough-basics" / "images"
SPECS = [
    ("cover.jpg", (1240, 1754), 0, "loaf", 0),
    ("starter-hero.jpg", (1600, 900), 3, "jar", 0),
    ("starter-feeding.jpg", (1600, 1000), 4, "jar", 1),
    ("starter-ready.jpg", (1600, 1000), 5, "bowl", 3),
    ("loaf-hero.jpg", (1600, 900), 6, "loaf", 0),
    ("shaping.jpg", (1600, 1000), 7, "bowl", 2),
    ("baked-loaf.jpg", (1600, 1000), 8, "loaf", 1),
]
for name, size, seed, motif, pal in SPECS:
    make_placeholder(IMG / name, "", size=size, seed=seed, motif=motif, palette=pal)
    print(IMG / name)
