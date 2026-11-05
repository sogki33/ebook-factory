"""Markdown chapter -> book HTML.

Supported on top of standard Markdown + tables:
  # Title            chapter title (one per file); the first paragraph after it is the lead
  ## Heading         numbered section (1-1, 1-2, ...)
  > [!TIP] Title     callout boxes: TIP, NOTE, DO, DONT, WARNING, IMPORTANT
  ![caption](x.jpg)  standalone image -> numbered figure with caption
  - [ ] item         printable checkbox (and - [x] for a ticked one)
Optional YAML front matter: image (chapter header art), label (e.g. "Appendix"), lead.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import markdown
import yaml

LABELS = {
    "en": {"chapter": "Chapter {n}", "short": "Ch. {n}", "contents": "Contents", "figure": "Figure",
           "TIP": "Tip", "NOTE": "Note", "DO": "Do this", "DONT": "Don't", "WARNING": "Warning",
           "IMPORTANT": "Important"},
    "ko": {"chapter": "{n}장", "short": "{n}장", "contents": "차례", "figure": "그림",
           "TIP": "팁", "NOTE": "참고", "DO": "이렇게 하세요", "DONT": "하지 마세요", "WARNING": "주의",
           "IMPORTANT": "중요"},
}
CALLOUT_CLASS = {"TIP": "tip", "NOTE": "note", "DO": "do", "DONT": "dont", "WARNING": "warn", "IMPORTANT": "imp"}


def labels(lang: str) -> dict:
    return LABELS.get(lang.split("-")[0], LABELS["en"])


@dataclass
class Section:
    sid: str
    number: str
    title: str


@dataclass
class Chapter:
    n: int
    path: Path
    title: str
    label: str
    lead: str
    image: str | None
    body_md: str
    sections: list[Section] = field(default_factory=list)
    figures: int = 0

    @property
    def cid(self) -> str:
        return f"ch{self.n}"


FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def parse_chapter(path: Path, n: int, lang: str) -> Chapter:
    text = path.read_text(encoding="utf-8")
    meta = {}
    m = FRONT.match(text)
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        text = text[m.end():]
    lines = text.splitlines()
    title, start = path.stem, 0
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            title, start = ln[2:].strip(), i + 1
            break
    rest = "\n".join(lines[start:]).strip("\n")
    lead = meta.get("lead", "")
    if not lead:
        # first plain paragraph right after the title becomes the lead
        blocks = re.split(r"\n\s*\n", rest.strip(), maxsplit=1)
        first = blocks[0].strip() if blocks else ""
        if first and not re.match(r"(#|>|!\[|\||[-*+] |\d+\. |```|<)", first):
            lead = first
            rest = blocks[1] if len(blocks) > 1 else ""
    label = meta.get("label") or labels(lang)["chapter"].format(n=n)
    ch = Chapter(n=n, path=path, title=title, label=str(label), lead=lead,
                 image=meta.get("image"), body_md=rest)
    k = 0
    for ln in rest.splitlines():
        if ln.startswith("## "):
            k += 1
            ch.sections.append(Section(f"ch{n}-s{k}", f"{n}-{k}", ln[3:].strip()))
    return ch


def _inline(md_text: str) -> str:
    out = markdown.markdown(md_text, extensions=["smarty"])
    return re.sub(r"^<p>|</p>$", "", out.strip())


CALLOUT_START = re.compile(r"^>\s?\[!(\w+)\][ \t]*(.*)$")


def expand_callouts(md_text: str, L: dict) -> str:
    """`> [!TIP] Title` blockquotes -> <div class="box tip" markdown="1"> blocks.

    Done before Markdown parsing so adjacent callouts never merge into one blockquote."""
    lines, out, i = md_text.splitlines(), [], 0
    while i < len(lines):
        m = CALLOUT_START.match(lines[i])
        if not m or m.group(1).upper() not in CALLOUT_CLASS:
            out.append(lines[i])
            i += 1
            continue
        kind = m.group(1).upper()
        head = m.group(2).strip() or L[kind]
        i += 1
        inner = []
        while i < len(lines) and lines[i].startswith(">"):
            inner.append(re.sub(r"^>\s?", "", lines[i]))
            i += 1
        out += ["", f'<div class="box {CALLOUT_CLASS[kind]}" markdown="1">', f'<div class="bh">{html.escape(head)}</div>',
                "", *inner, "", "</div>", ""]
    return "\n".join(out)


def chapter_html(ch: Chapter, lang: str, resolve_img: Callable[[str, Path], str], markers: bool = False) -> str:
    L = labels(lang)
    exts = ["tables", "sane_lists", "attr_list", "fenced_code", "md_in_html"] + (["smarty"] if lang.startswith("en") else [])
    body = markdown.markdown(expand_callouts(ch.body_md, L), extensions=exts)

    # numbered sections
    k = 0

    def h2(m):
        nonlocal k
        k += 1
        s = ch.sections[k - 1]
        mk = f'<span class="ef-mk">@@EF:{s.sid}@@</span>' if markers else ""
        return f'<h2 id="{s.sid}">{mk}<span class="n">{s.number}</span>{m.group(1)}</h2>'
    body = re.sub(r"<h2>(.*?)</h2>", h2, body, flags=re.S)

    # figures
    fig = 0

    def figure(m):
        nonlocal fig
        attrs = m.group(1)
        src = re.search(r'src="([^"]+)"', attrs).group(1)
        alt_m = re.search(r'alt="([^"]*)"', attrs)
        cap = html.unescape(alt_m.group(1)) if alt_m else ""
        fig += 1
        url = resolve_img(html.unescape(src), ch.path)
        capt = f'<figcaption><b>{L["figure"]} {ch.n}-{fig}.</b> {html.escape(cap)}</figcaption>' if cap else ""
        return f'<figure class="fig"><img src="{html.escape(url)}" alt="{html.escape(cap)}">{capt}</figure>'
    body = re.sub(r"<p>\s*<img([^>]*?)/?>\s*</p>", figure, body)
    ch.figures = fig
    # inline (non-standalone) images still need path resolution
    body = re.sub(r'(<img[^>]*?src=")(?!file:|data:|https?:)([^"]+)"',
                  lambda m: m.group(1) + html.escape(resolve_img(html.unescape(m.group(2)), ch.path)) + '"', body)

    # checklists
    body = re.sub(r"<li>(\s*<p>)?\s*\[( |x|X)\]\s*",
                  lambda m: f'<li class="task{" done" if m.group(2) != " " else ""}">{m.group(1) or ""}<span class="cb"></span>',
                  body)
    body = re.sub(r"<ul>(\s*<li class=\"task)", r'<ul class="checklist">\1', body)

    art = ""
    if ch.image:
        art = f'<div class="ch-art" style="background-image:url(\'{resolve_img(ch.image, ch.path)}\')"></div>'
    mk = f'<span class="ef-mk">@@EF:{ch.cid}@@</span>' if markers else ""
    lead = f'<p class="lead">{_inline(ch.lead)}</p>' if ch.lead else ""
    head = (f'<header class="ch-head{" has-art" if art else ""}">{art}{mk}<div class="no">{html.escape(ch.label)}</div>'
            f'<h1>{html.escape(ch.title)}</h1>{lead}</header>')
    return f'<section class="ch" id="{ch.cid}">{head}{body}</section>'
