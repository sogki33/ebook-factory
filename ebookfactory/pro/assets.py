"""Marketing assets rendered from HTML (Pro): store cover, thumbnail, carousel, pins."""
from __future__ import annotations

import base64
import html
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from ..builder import Renderer, load_chapters
from ..config import Book
from ..images import ImageResolver
from ..licensing import WATERMARK
from ..theme import SANS, SERIF, resolve_theme

TXT = {
    "en": {"swipe": "Swipe →", "inside": "Inside this chapter", "get": "Get the full book", "free": "Free sampler",
           "pages": "{p} pages", "figs": "{f} illustrations", "pdf": "PDF", "save": "Save for later"},
    "ko": {"swipe": "넘겨보기 →", "inside": "이 장에서 다루는 것", "get": "정식판 받기", "free": "무료 맛보기",
           "pages": "{p}쪽", "figs": "그림 {f}점", "pdf": "PDF", "save": "저장해 두세요"},
}


def _uri(p: Path | None) -> str:
    if not p or not p.exists():
        return ""
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def _fit(text: str, base: float, chars: int) -> int:
    """Shrink headline font size for long titles."""
    n = max(len(text), 1)
    return int(base if n <= chars else max(base * 0.55, base * chars / n))


def _clip(text: str, n: int) -> str:
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0] if " " in text[:n] else text[:n]
    return cut.rstrip(",.;:—- ") + "…"


def _domain(url: str) -> str:
    if not url:
        return ""
    u = urlparse(url)
    return (u.netloc + u.path).rstrip("/").removeprefix("www.")


def _page(w, h, body, theme, wm, extra_css=""):
    head = SERIF if theme.get("font") == "serif" else SANS
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{w}px;height:{h}px;overflow:hidden;font-family:{SANS};background:{theme['dark']};color:#fff;word-break:keep-all}}
.h{{font-family:{head};font-weight:900;letter-spacing:-.02em;line-height:1.05}}
.tag{{display:inline-block;white-space:nowrap;background:{theme['highlight']};color:#111;font-weight:800;border-radius:8px;letter-spacing:.06em;text-transform:uppercase}}
.acc{{color:{theme['highlight']}}}
.wm{{position:absolute;right:14px;bottom:10px;font-size:13px;color:rgba(255,255,255,.55);z-index:9}}
{extra_css}</style></head><body><div style="position:relative;width:{w}px;height:{h}px;overflow:hidden">{body}
{f'<div class="wm">{WATERMARK}</div>' if wm else ''}</div></body></html>"""


def _pdf_page_png(pdf: Path, page: int, out: Path, width: int = 900) -> Path | None:
    if not pdf.exists() or not shutil.which("pdftoppm"):
        return None
    stem = out.with_suffix("")
    subprocess.run(["pdftoppm", "-png", "-f", str(page), "-l", str(page), "-scale-to-x", str(width), "-scale-to-y", "-1",
                    "-singlefile", str(pdf), str(stem)], check=True, capture_output=True)
    return out if out.exists() else None


def _page_count(book: Book) -> int | None:
    pdf = book.out / f"{book.slug}.pdf"
    pages = None
    if pdf.exists():
        from pypdf import PdfReader
        pages = len(PdfReader(str(pdf)).pages)
    return pages


def build_assets(book: Book, pro: bool, rd: Renderer | None = None) -> list[Path]:
    if rd is None:
        with Renderer() as r:
            return build_assets(book, pro, r)
    T = TXT.get(book.language.split("-")[0], TXT["en"])
    theme = resolve_theme(book, pro)
    e = html.escape
    wm = not pro
    out = book.out / "assets"
    out.mkdir(parents=True, exist_ok=True)
    res = ImageResolver(book.root, book.out / ".cache", "phone")
    chapters = load_chapters(book)
    # resolve chapter images (header art, else first figure)
    for c in chapters:
        src = c.image
        if not src:
            m = re.search(r"!\[[^\]]*\]\(([^)\s]+)", c.body_md)
            src = m.group(1) if m else None
        p = res.find(src, c.path) if src else None
        c._img = _uri(res.variant_path(p)) if p else ""
    cover_p = res.find(book.cover_image) if book.cover_image else None
    cover = _uri(res.variant_path(cover_p)) if cover_p else (chapters[0]._img if chapters else "")
    pages = _page_count(book)
    figs = sum(len(re.findall(r"^\s*!\[", c.body_md, re.M)) for c in chapters)
    tagline = book.tagline or " · ".join(x for x in [
        T["pages"].format(p=pages) if pages else "", T["figs"].format(f=figs) if figs else "", T["pdf"]] if x)
    mock = _pdf_page_png(book.out / f"{book.slug}.pdf", 1, book.out / ".work" / "cover-page.png")
    made: list[Path] = []

    def shot(name, w, h, body, css=""):
        p = out / name
        rd.screenshot(_page(w, h, body, theme, wm, css), p, w, h)
        made.append(p)

    title, sub = e(book.title), e(book.subtitle)
    bg = lambda uri, op=.9: f'<img src="{uri}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:{op}">' if uri else ""

    # 1) store cover 1280x720 (Gumroad / Etsy listing)
    book_img = (f'<img src="{_uri(mock)}" style="position:absolute;right:90px;top:70px;height:580px;border-radius:6px;'
                f'box-shadow:0 30px 60px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.08);transform:rotate(3deg)">') if mock else ""
    shot("cover-1280x720.jpg", 1280, 720, f"""
{bg(cover, .55)}<div style="position:absolute;inset:0;background:linear-gradient(90deg,{theme['dark']} 0%,{theme['dark']}e6 45%,{theme['dark']}33 100%)"></div>
{book_img}<div style="position:absolute;left:76px;top:0;bottom:0;width:{620 if mock else 900}px;display:flex;flex-direction:column;justify-content:center">
<div><span class="tag" style="font-size:20px;padding:8px 16px">{e(tagline)}</span></div>
<div class="h" style="font-size:{_fit(book.title, 84, 18 if mock else 26)}px;margin:26px 0 20px">{title}</div>
<div style="font-size:28px;line-height:1.35;color:#e7e5e4;font-weight:500">{sub}</div>
<div style="font-size:18px;letter-spacing:.2em;text-transform:uppercase;color:#a8a29e;margin-top:28px;font-weight:700">{e(book.author)}</div></div>""")

    # 2) square thumbnail 600x600
    shot("thumb-600x600.jpg", 600, 600, f"""
{bg(cover)}<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 30%,{theme['dark']}f2 82%)"></div>
<div style="position:absolute;left:40px;right:40px;bottom:44px">
<div class="h" style="font-size:{_fit(book.title, 64, 16)}px">{title}</div>
<div style="font-size:21px;margin-top:12px;color:#e7e5e4;line-height:1.3">{sub}</div></div>""")

    # 3) Instagram carousel 1080x1350: hook, one slide per chapter, CTA
    n_slides = len(chapters) + 2
    ctr = lambda i: f'<div style="position:absolute;top:44px;right:56px;font-size:24px;font-weight:700;color:rgba(255,255,255,.7)">{i}/{n_slides}</div>'
    shot("carousel-01.jpg", 1080, 1350, f"""
{bg(cover, .8)}<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.1) 20%,{theme['dark']}f5 78%)"></div>{ctr(1)}
<div style="position:absolute;left:80px;right:80px;bottom:120px"><span class="tag" style="font-size:24px;padding:10px 20px">{e(tagline)}</span>
<div class="h" style="font-size:{_fit(book.title, 118, 14)}px;margin:34px 0 26px">{title}</div>
<div style="font-size:36px;line-height:1.35;color:#e7e5e4">{sub}</div>
<div style="font-size:30px;font-weight:800;margin-top:44px" class="acc">{T['swipe']}</div></div>""")
    for i, c in enumerate(chapters, 2):
        secs = "".join(f'<li><span class="acc" style="font-weight:800;margin-right:18px">{s.number}</span>{e(s.title)}</li>'
                       for s in c.sections[:6])
        shot(f"carousel-{i:02d}.jpg", 1080, 1350, f"""
<div style="position:absolute;left:0;right:0;top:0;height:560px">{bg(c._img, 1)}<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 50%,{theme['dark']} 100%)"></div></div>{ctr(i)}
<div style="position:absolute;left:80px;right:80px;top:520px">
<div style="font-size:26px;font-weight:800;letter-spacing:.3em;text-transform:uppercase" class="acc">{e(c.label)}</div>
<div class="h" style="font-size:{_fit(c.title, 80, 20)}px;margin:18px 0 40px">{e(c.title)}</div>
<div style="font-size:22px;letter-spacing:.15em;text-transform:uppercase;color:#a8a29e;font-weight:700;margin-bottom:16px">{T['inside']}</div>
<ul style="list-style:none;font-size:34px;line-height:1.35">{secs}</ul></div>""",
             "li{padding:16px 0;border-bottom:2px solid rgba(255,255,255,.12)}")
    links = "".join(f'<div style="margin-top:26px"><div style="font-size:24px;color:#a8a29e;font-weight:700;letter-spacing:.12em;text-transform:uppercase">{lab}</div>'
                    f'<div style="font-size:38px;font-weight:800">{e(_domain(u))}</div></div>'
                    for lab, u in ((T["get"], book.buy_url), (T["free"], book.free_url)) if u)
    shot(f"carousel-{n_slides:02d}.jpg", 1080, 1350, f"""
{bg(cover, .35)}<div style="position:absolute;inset:0;background:{theme['dark']}c0"></div>{ctr(n_slides)}
<div style="position:absolute;left:80px;right:80px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center">
<div class="h" style="font-size:{_fit(book.title, 96, 16)}px">{title}</div>
<div style="font-size:34px;margin:24px 0 30px;color:#e7e5e4">{e(str(book.price))} {('· ' + e(tagline)) if tagline else ''}</div>
<div style="height:6px;width:120px;background:{theme['highlight']};margin-bottom:10px"></div>{links}</div>""")

    # 4) Pinterest pins 1000x1500, one per chapter (point to the free sampler when there is one)
    target = book.free_url or book.buy_url
    target_lab = T["free"] if book.free_url else T["get"]
    for i, c in enumerate(chapters, 1):
        shot(f"pin-{i:02d}.jpg", 1000, 1500, f"""
<div style="position:absolute;left:0;right:0;top:0;height:860px">{bg(c._img, 1)}</div>
<div style="position:absolute;left:0;right:0;top:800px;bottom:0;background:{theme['dark']};border-radius:40px 40px 0 0;padding:70px 72px">
<div style="font-size:26px;font-weight:800;letter-spacing:.3em;text-transform:uppercase" class="acc">{e(book.title)}</div>
<div class="h" style="font-size:{_fit(c.title, 84, 18)}px;margin:22px 0 26px">{e(c.title)}</div>
<div style="font-size:30px;line-height:1.4;color:#d6d3d1">{e(_clip(re.sub(r'[*_`]', '', c.lead), 150))}</div>
<div style="position:absolute;left:72px;right:72px;bottom:64px;display:flex;justify-content:space-between;align-items:center">
<span class="tag" style="font-size:24px;padding:12px 22px">{target_lab} →</span><span style="font-size:26px;color:#a8a29e">{e(_domain(target))}</span></div></div>""")
    return made
