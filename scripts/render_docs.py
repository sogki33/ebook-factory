"""Build the demo book and render the README screenshots into docs/.

    python scripts/render_docs.py
Requires pdftoppm (poppler-utils). Set EBOOKFACTORY_KEY to render assets without the preview watermark.
"""
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "sourdough-basics"
DIST = DEMO / "dist"
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)


def ef(*a):
    subprocess.run([sys.executable, "-m", "ebookfactory", *a, "--book", str(DEMO)], cwd=ROOT, check=True)


def page(pdf, n, out, dpi=110):
    stem = DOCS / out
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(n), "-l", str(n), "-singlefile", str(pdf), str(stem)],
                   check=True)
    return Image.open(f"{stem}.png")


ef("build")
ef("sampler", "--chapters", "1")
ef("assets")
book = DIST / "sourdough-basics.pdf"
pages = [page(book, n, name) for n, name in [(1, "page-cover"), (2, "page-toc"), (3, "page-chapter"), (6, "page-callouts")]]
page(DIST / "sourdough-basics-sampler.pdf", 7, "sampler-cta")

# hero strip: four pages side by side
w, h = pages[0].size
gap = 24
hero = Image.new("RGB", (w * 4 + gap * 5, h + gap * 2), (231, 229, 228))
for i, im in enumerate(pages):
    hero.paste(im, (gap + i * (w + gap), gap))
hero.save(DOCS / "hero.png", optimize=True)

A = DIST / "assets"
shutil.copy(A / "cover-1280x720.jpg", DOCS / "asset-cover-1280x720.jpg")
row = [Image.open(A / f) for f in ("thumb-600x600.jpg", "carousel-01.jpg", "carousel-02.jpg", "pin-01.jpg")]
H = 540
row = [im.resize((round(im.width * H / im.height), H), Image.LANCZOS) for im in row]
strip = Image.new("RGB", (sum(im.width for im in row) + gap * (len(row) + 1), H + gap * 2), (231, 229, 228))
x = gap
for im in row:
    strip.paste(im, (x, gap))
    x += im.width + gap
strip.save(DOCS / "assets-strip.jpg", quality=88)
print("\n".join(str(p) for p in sorted(DOCS.iterdir())))
