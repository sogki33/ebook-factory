"""Image lookup + print/phone variants."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageOps

PHONE_MAX = 1000   # px on the long edge for the phone-friendly PDF
PRINT_MAX = 2600   # cap absurdly large originals (A5 @ 300dpi ~ 1750px wide)


class ImageResolver:
    """Maps a Markdown image reference to a file:// URL of the right variant."""

    def __init__(self, root: Path, cache: Path, variant: str = "print"):
        self.root, self.variant = root, variant
        self.cache = cache / variant
        self.cache.mkdir(parents=True, exist_ok=True)
        self.missing: list[str] = []
        self.used: list[Path] = []

    def find(self, src: str, chapter: Path | None = None) -> Path | None:
        if src.startswith(("http://", "https://", "data:", "file:")):
            return None
        cands = [self.root / src]
        if chapter is not None:
            cands.append(chapter.parent / src)
        return next((c.resolve() for c in cands if c.exists()), None)

    def __call__(self, src: str, chapter: Path | None = None) -> str:
        if src.startswith(("http://", "https://", "data:", "file:")):
            return src
        p = self.find(src, chapter)
        if p is None:
            self.missing.append(src)
            print(f"  ! missing image: {src}", file=sys.stderr)
            return self._placeholder(src).as_uri()
        self.used.append(p)
        return self.variant_path(p).as_uri()

    def variant_path(self, p: Path) -> Path:
        limit = PHONE_MAX if self.variant == "phone" else PRINT_MAX
        st = p.stat()
        key = hashlib.sha1(f"{p}:{st.st_mtime_ns}:{st.st_size}:{limit}".encode()).hexdigest()[:16]
        out = self.cache / f"{p.stem}-{key}.jpg"
        if out.exists():
            return out
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im)
            if self.variant == "print" and max(im.size) <= limit and p.suffix.lower() in (".jpg", ".jpeg"):
                return p  # already fine, embed the original bytes
            if im.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", im.size, "white")
                im = im.convert("RGBA")
                bg.paste(im, mask=im.split()[-1])
                im = bg
            im = im.convert("RGB")
            im.thumbnail((limit, limit), Image.LANCZOS)
            im.save(out, "JPEG", quality=72 if self.variant == "phone" else 88, optimize=True, progressive=True)
        return out

    def _placeholder(self, src: str) -> Path:
        from .placeholder import make_placeholder
        out = self.cache / ("missing-" + hashlib.sha1(src.encode()).hexdigest()[:10] + ".jpg")
        if not out.exists():
            make_placeholder(out, f"missing: {src}", size=(1200, 800), seed=7)
        return out
