"""`ebookfactory init` — create a new book project."""
from __future__ import annotations

from pathlib import Path

from .placeholder import make_placeholder

BOOK_YAML = """\
# ebook-factory book configuration
title: "{title}"
subtitle: "A short, practical guide"
author: "Your Name"
language: en            # en, ko, ja ... (sets fonts, hyphenation and built-in labels)
page_size: A5           # A5 (default), Letter, 6x9
theme: classic          # classic (free) | midnight, sage, rose (Pro)
colors:                 # optional overrides
  accent: "#c2410c"
  dark: "#1c1917"
  highlight: "#f97316"
cover_image: images/cover.jpg
cover_tag: "Illustrated guide"
price: "$9"
buy_url: "https://example.gumroad.com/l/my-book"
free_url: "https://example.gumroad.com/l/my-book-sampler"
intro_box:              # optional box under the table of contents (delete to hide)
  title: "Save this on your phone"
  text: "Download this PDF to your phone's Files app and share it with the people who need it."
notice: ""              # optional small print under the table of contents
sampler:
  chapters: [1]         # default chapters for `ebookfactory sampler`
"""

CHAPTER = """\
# Getting Started

This first paragraph becomes the chapter's lead text in the dark header band. Keep it to two or three sentences.

## Write in plain Markdown

Every `##` heading becomes a numbered section (1-1, 1-2, ...) and an entry in the table of contents with its real page number.

![A caption under the picture becomes a numbered figure](images/example.jpg)

> [!TIP]
> Callouts use GitHub-style markers: `[!TIP]`, `[!NOTE]`, `[!DO]`, `[!DONT]`, `[!WARNING]` and `[!IMPORTANT]`.

## Checklists and tables

- [ ] Printable checkboxes
- [ ] Render as real boxes on paper
- [x] Ticked ones work too

| Feature | Syntax |
|---|---|
| Section | `## Title` |
| Figure | `![caption](images/x.jpg)` |

> [!DONT] Avoid this
> Don't paste screenshots of text. Write the text.
"""

GITIGNORE = "dist/\n"


def init_book(target: Path, title: str | None = None, force: bool = False) -> list[Path]:
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    cfg = target / "book.yaml"
    if cfg.exists() and not force:
        raise FileExistsError(f"{cfg} already exists (use --force to overwrite)")
    title = title or target.name.replace("-", " ").replace("_", " ").title()
    (target / "chapters").mkdir(exist_ok=True)
    (target / "images").mkdir(exist_ok=True)
    made = []
    cfg.write_text(BOOK_YAML.format(title=title.replace('"', "'")), encoding="utf-8")
    made.append(cfg)
    ch = target / "chapters" / "01-intro.md"
    if force or not ch.exists():
        ch.write_text(CHAPTER, encoding="utf-8")
        made.append(ch)
    for name, seed, motif in (("cover.jpg", 1, "wheat"), ("example.jpg", 2, "bowl")):
        p = target / "images" / name
        if force or not p.exists():
            make_placeholder(p, "placeholder — replace me", size=(1240, 1754) if name == "cover.jpg" else (1600, 1000),
                             seed=seed, motif=motif)
            made.append(p)
    gi = target / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE)
    return made
