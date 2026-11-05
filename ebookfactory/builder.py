"""Assemble book HTML and render it to PDF with Playwright Chromium (two-pass TOC)."""
from __future__ import annotations

import base64
import html
import io
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Book
from .images import ImageResolver
from .licensing import WATERMARK
from .render_md import Chapter, chapter_html, labels, parse_chapter
from .theme import book_css, resolve_theme

import logging
logging.getLogger("pypdf").setLevel(logging.ERROR)

MARK = re.compile(r"@@EF:([\w-]+)@@")


class Renderer:
    """One Chromium instance reused for every pass / output."""

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        try:
            self.browser = self._pw.chromium.launch()
        except Exception as e:  # pragma: no cover - environment specific
            self._pw.stop()
            raise SystemExit(f"Could not launch Chromium ({e}).\nRun: python -m playwright install chromium")
        return self

    def __exit__(self, *exc):
        self.browser.close()
        self._pw.stop()

    def pdf(self, html_file: Path, out: Path, book: Book):
        w, h = book.page_mm
        page = self.browser.new_page()
        page.goto(html_file.as_uri(), wait_until="load")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(200)
        page.pdf(path=str(out), width=f"{w}mm", height=f"{h}mm", print_background=True,
                 outline=True, tagged=True, prefer_css_page_size=True)
        page.close()

    def screenshot(self, html_str: str, out: Path, w: int, h: int, quality: int = 90):
        page = self.browser.new_page(viewport={"width": w, "height": h})
        page.set_content(html_str, wait_until="load")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(150)
        kw = {"type": "jpeg", "quality": quality} if out.suffix.lower() in (".jpg", ".jpeg") else {"type": "png"}
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": w, "height": h}, **kw)
        page.close()


def page_texts(pdf: Path) -> list[str]:
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True)
        pages = r.stdout.split("\f")
        return pages[:-1] if pages and not pages[-1].strip() else pages
    from pypdf import PdfReader
    return [p.extract_text() or "" for p in PdfReader(str(pdf)).pages]


def find_pages(pdf: Path) -> dict[str, int]:
    found: dict[str, int] = {}
    for i, t in enumerate(page_texts(pdf), 1):
        for m in MARK.finditer(t.replace(" ", "")):
            found.setdefault(m.group(1), i)
    return found


def load_chapters(book: Book) -> list[Chapter]:
    return [parse_chapter(p, i, book.language) for i, p in enumerate(book.chapter_files(), 1)]


def _data_uri_qr(url: str) -> str | None:
    try:
        import qrcode
    except ImportError:
        return None
    img = qrcode.make(url, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@dataclass
class Extra:
    """A non-Markdown section (e.g. the sampler CTA) that still gets a TOC row."""
    sid: str
    label: str
    title: str
    html: str


def assemble(book: Book, chapters: list[Chapter], resolver: ImageResolver, pages: dict[str, int], *,
             markers: bool, pro: bool, cover_tag: str = "", extras: list[Extra] | None = None,
             watermark: bool = False, toc_depth: int = 2) -> str:
    L = labels(book.language)
    theme = resolve_theme(book, pro)
    e = html.escape
    bodies = [chapter_html(c, book.language, resolver, markers=markers) for c in chapters]
    extras = extras or []
    for x in extras:
        mk = f'<span class="ef-mk">@@EF:{x.sid}@@</span>' if markers else ""
        bodies.append(x.html.replace("<!--MK-->", mk))

    # cover
    cover_img = ""
    if book.cover_image:
        cover_img = f'<img src="{e(resolver(book.cover_image))}" alt="">'
    tag = cover_tag or book.cover_tag
    cover = (f'<div class="cover">{cover_img}<div class="shade"></div><div class="in">'
             + (f'<div class="tag">{e(tag)}</div>' if tag else "")
             + f'<div class="title">{e(book.title)}</div>'
             + (f'<p class="sub">{e(book.subtitle)}</p>' if book.subtitle else "")
             + (f'<div class="by">{e(book.author)}</div>' if book.author else "")
             + "</div></div>")

    # table of contents
    def pg(k):
        return str(pages.get(k, ""))
    rows = []
    for c in chapters:
        rows.append(f'<a class="c" href="#{c.cid}"><span class="s">{e(c.label)}</span><span class="t">{e(c.title)}</span>'
                    f'<span class="p">{pg(c.cid)}</span></a>')
        if toc_depth >= 2:
            for s in c.sections:
                rows.append(f'<a class="x" href="#{s.sid}"><span class="s">{s.number}</span><span class="t">{e(s.title)}</span>'
                            f'<span class="p">{pg(s.sid)}</span></a>')
    for x in extras:
        rows.append(f'<a class="c" href="#{x.sid}"><span class="s">{e(x.label)}</span><span class="t">{e(x.title)}</span>'
                    f'<span class="p">{pg(x.sid)}</span></a>')
    intro = ""
    if book.intro_box:
        ib = book.intro_box
        intro = (f'<div class="box imp intro-box"><div class="bh">{e(str(ib.get("title", "")))}</div>'
                 f'<p>{e(str(ib.get("text", "")))}</p></div>')
    notice = f'<p class="notice">{e(book.notice)}</p>' if book.notice else ""
    toc = (f'<div class="front"><h1 class="toc-h" id="toc">{L["contents"]}</h1><nav class="toc">{"".join(rows)}</nav>'
           f'{intro}{notice}</div>')
    wm_css = (f'@page{{@bottom-right{{content:"{WATERMARK}";font-size:6pt;color:#a8a29e}}}}'
              f'@page front{{@bottom-right{{content:"{WATERMARK}"}}}}') if watermark else ""
    return (f'<!doctype html><html lang="{e(book.language)}"><head><meta charset="utf-8">'
            f'<title>{e(book.title)}</title><meta name="author" content="{e(book.author)}">'
            f'<style>{book_css(book, theme)}{wm_css}</style></head><body>{cover}{toc}{"".join(bodies)}</body></html>')


def set_metadata(pdf: Path, book: Book, subject: str = ""):
    from pypdf import PdfReader, PdfWriter
    r = PdfReader(str(pdf))
    w = PdfWriter(clone_from=r)
    w.add_metadata({"/Title": book.title, "/Author": book.author or "", "/Subject": subject or book.subtitle or "",
                    "/Creator": "ebook-factory", "/Lang": book.language})
    tmp = pdf.with_suffix(".tmp.pdf")
    with open(tmp, "wb") as f:
        w.write(f)
    tmp.replace(pdf)


@dataclass
class BuildResult:
    pdf: Path
    pages: int
    toc: dict[str, int]
    figures: int
    missing_images: list[str]


def build_pdf(rd: Renderer, book: Book, chapters: list[Chapter], out: Path, *, variant: str, pro: bool,
              cover_tag: str = "", extras: list[Extra] | None = None, watermark: bool = False,
              subject: str = "") -> BuildResult:
    work = book.out / ".work"
    work.mkdir(exist_ok=True)
    resolver = ImageResolver(book.root, book.out / ".cache", variant)
    html_file = work / (out.stem + ".html")
    kw = dict(pro=pro, cover_tag=cover_tag, extras=extras, watermark=watermark)
    # pass 1: invisible-in-final markers tell us where every chapter/section landed
    html_file.write_text(assemble(book, chapters, resolver, {}, markers=True, **kw), encoding="utf-8")
    rd.pdf(html_file, out, book)
    toc = find_pages(out)
    # pass 2: same layout (markers are absolutely positioned), now with page numbers
    resolver.missing.clear()
    html_file.write_text(assemble(book, chapters, resolver, toc, markers=False, **kw), encoding="utf-8")
    rd.pdf(html_file, out, book)
    set_metadata(out, book, subject)
    from pypdf import PdfReader
    n = len(PdfReader(str(out)).pages)
    return BuildResult(out, n, toc, sum(c.figures for c in chapters), sorted(set(resolver.missing)))
