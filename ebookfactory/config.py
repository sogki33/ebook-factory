"""book.yaml loading and defaults."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PAGE_SIZES = {
    # name: (width_mm, height_mm)
    "A5": (148.0, 210.0),
    "Letter": (215.9, 279.4),
    "6x9": (152.4, 228.6),
}

DEFAULT_THEME = {
    "accent": "#c2410c",   # section badges, chapter labels
    "dark": "#1c1917",     # chapter header band, cover tint
    "ink": "#1c1917",      # body text
    "highlight": "#f97316",  # cover tag, chapter number
}


class ConfigError(Exception):
    pass


@dataclass
class Book:
    root: Path
    title: str
    subtitle: str = ""
    author: str = ""
    language: str = "en"
    page_size: str = "A5"
    theme: str = "classic"
    colors: dict = field(default_factory=dict)
    cover_image: str | None = None
    cover_tag: str = ""
    buy_url: str = ""
    free_url: str = ""
    price: str = ""
    tagline: str = ""
    intro_box: dict | None = None
    notice: str = ""
    chapters_dir: str = "chapters"
    output_dir: str = "dist"
    sampler: dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        s = re.sub(r"[^\w\s-]", "", self.title, flags=re.UNICODE).strip().lower()
        s = re.sub(r"[\s_]+", "-", s)
        return s or "book"

    @property
    def page_mm(self) -> tuple[float, float]:
        return PAGE_SIZES[self.page_size]

    @property
    def out(self) -> Path:
        p = (self.root / self.output_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def path(self, rel: str | None) -> Path | None:
        if not rel:
            return None
        p = Path(rel)
        return p if p.is_absolute() else (self.root / p).resolve()

    def chapter_files(self) -> list[Path]:
        d = self.root / self.chapters_dir
        files = sorted(p for p in d.glob("*.md") if not p.name.startswith("_"))
        if not files:
            raise ConfigError(f"No chapters found in {d} (expected *.md files)")
        return files


def find_book(start: str | Path | None) -> Path:
    p = Path(start or ".").resolve()
    if p.is_file():
        return p
    for cand in (p / "book.yaml", p / "book.yml"):
        if cand.exists():
            return cand
    raise ConfigError(f"No book.yaml found in {p}. Run `ebookfactory init <dir>` first or pass --book.")


def load_book(start: str | Path | None = None) -> Book:
    cfg_path = find_book(start)
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not data.get("title"):
        raise ConfigError(f"{cfg_path}: 'title' is required")
    page_size = str(data.get("page_size", "A5"))
    match = {k.lower(): k for k in PAGE_SIZES}
    if page_size.lower() not in match:
        raise ConfigError(f"page_size must be one of {', '.join(PAGE_SIZES)} (got {page_size!r})")
    theme_val = data.get("theme", "classic")
    colors = dict(data.get("colors") or {})
    if isinstance(theme_val, dict):  # allow `theme: {name: ..., accent: ...}`
        colors.update({k: v for k, v in theme_val.items() if k != "name"})
        theme_val = theme_val.get("name", "classic")
    known = {f for f in Book.__dataclass_fields__} - {"root", "colors", "theme", "page_size"}
    kwargs = {k: v for k, v in data.items() if k in known}
    for k in ("cover", "cover_image"):
        if data.get(k):
            kwargs["cover_image"] = data[k]
    return Book(root=cfg_path.parent.resolve(), page_size=match[page_size.lower()],
                theme=str(theme_val), colors=colors, **kwargs)
