"""ebookfactory command line."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import __version__
from .config import ConfigError, load_book
from .licensing import activate, is_pro


def _size(p: Path) -> str:
    b = p.stat().st_size
    return f"{b / 1e6:.1f} MB" if b >= 1e6 else f"{b / 1e3:.0f} KB"


def _report(label, r):
    toc = ", ".join(f"{k}→p{v}" for k, v in r.toc.items() if "-s" not in k)
    print(f"  {label:<7} {r.pdf}  ({r.pages} pages, {_size(r.pdf)})")
    print(f"          chapters: {toc}")
    if r.missing_images:
        print(f"          missing images: {', '.join(r.missing_images)}")


def _preview_note(what):
    print(f"  · {what} rendered in preview mode (watermarked). Run `ebookfactory activate <KEY>` to unlock Pro.")


def cmd_init(a):
    from .scaffold import init_book
    made = init_book(Path(a.dir), a.title, a.force)
    for p in made:
        print(f"  + {p}")
    print(f"\nNext:\n  cd {a.dir}\n  ebookfactory build")


def cmd_build(a):
    from .builder import Renderer, build_pdf, load_chapters
    book = load_book(a.book)
    pro = is_pro()
    if book.theme != "classic" and not pro:
        print(f"  · theme '{book.theme}' is a Pro theme; using 'classic'. Run `ebookfactory activate <KEY>` to unlock.")
    chapters = load_chapters(book)
    t = time.time()
    print(f"Building “{book.title}” — {len(chapters)} chapter(s), {book.page_size}")
    with Renderer() as rd:
        r = build_pdf(rd, book, chapters, book.out / f"{book.slug}.pdf", variant="print", pro=pro)
        _report("print", r)
        if not a.no_phone:
            r2 = build_pdf(rd, book, chapters, book.out / f"{book.slug}-phone.pdf", variant="phone", pro=pro)
            _report("phone", r2)
    print(f"Done in {time.time() - t:.1f}s")


def cmd_sampler(a):
    from .pro.sampler import build_sampler
    book = load_book(a.book)
    pro = is_pro()
    r = build_sampler(book, a.chapters, pro)
    _report("sampler", r)
    if not pro:
        _preview_note("Sampler")


def cmd_assets(a):
    from .pro.assets import build_assets
    book = load_book(a.book)
    if not (book.out / f"{book.slug}.pdf").exists():
        print("  · tip: run `ebookfactory build` first so the store cover shows the real cover page and page count")
    pro = is_pro()
    for p in build_assets(book, pro):
        print(f"  + {p}  ({_size(p)})")
    if not pro:
        _preview_note("Assets")


def cmd_activate(a):
    try:
        ok, msg = activate(a.key)
    except OSError as e:
        print(f"  · could not reach the license server: {e}")
        sys.exit(2)
    if ok:
        print(f"  ✓ Pro unlocked ({msg})")
    else:
        print(f"  ✗ {msg}")
        sys.exit(1)


def cmd_all(a):
    a.no_phone = False
    cmd_build(a)
    a.chapters = None
    cmd_sampler(a)
    cmd_assets(a)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ebookfactory",
                                 description="Markdown chapters + images -> print-quality PDF ebook and sales assets.")
    ap.add_argument("--version", action="version", version=f"ebookfactory {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="scaffold a new book (book.yaml, chapters/, images/)")
    p.add_argument("dir")
    p.add_argument("--title")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    def book_arg(p):
        p.add_argument("--book", "-b", default=".", help="book directory or book.yaml (default: .)")

    p = sub.add_parser("build", help="build the print PDF and the phone-friendly PDF")
    book_arg(p)
    p.add_argument("--no-phone", action="store_true", help="skip the downscaled phone edition")
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("sampler", help="[Pro] free lead-magnet PDF from selected chapters + CTA page")
    book_arg(p)
    p.add_argument("--chapters", "-c", help="e.g. 1,3 or 1-2 (default: sampler.chapters in book.yaml, else 1)")
    p.set_defaults(fn=cmd_sampler)

    p = sub.add_parser("assets", help="[Pro] store cover, thumbnail, Instagram carousel, Pinterest pins")
    book_arg(p)
    p.set_defaults(fn=cmd_assets)

    p = sub.add_parser("all", help="build + sampler + assets")
    book_arg(p)
    p.set_defaults(fn=cmd_all)

    p = sub.add_parser("activate", help="unlock Pro with the license key from your Gumroad receipt")
    p.add_argument("key")
    p.set_defaults(fn=cmd_activate)

    a = ap.parse_args(argv)
    try:
        a.fn(a)
    except (ConfigError, FileExistsError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
