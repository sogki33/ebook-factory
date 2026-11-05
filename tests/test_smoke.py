"""Smoke tests: build the demo book end to end and check the PDF really has a TOC with page numbers."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "sourdough-basics"


def run(*args, cwd=ROOT):
    r = subprocess.run([sys.executable, "-m", "ebookfactory", *args], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def text_pages(pdf):
    return [p.extract_text() or "" for p in PdfReader(str(pdf)).pages]


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    book = tmp_path_factory.mktemp("demo") / "sourdough-basics"
    shutil.copytree(DEMO, book, ignore=shutil.ignore_patterns("dist"))
    run("build", "--book", str(book))
    return book


def test_build_page_count_and_toc(demo):
    pdf = demo / "dist" / "sourdough-basics.pdf"
    reader = PdfReader(str(pdf))
    assert len(reader.pages) > 4
    toc = reader.pages[1].extract_text()
    assert "Contents" in toc
    # every TOC row ends with a page number; chapter 2 must point past chapter 1
    rows = dict(re.findall(r"(Your First Starter|Your First Loaf)\s*(\d+)", toc))
    assert set(rows) == {"Your First Starter", "Your First Loaf"}, toc
    assert int(rows["Your First Loaf"]) > int(rows["Your First Starter"]) >= 3
    # the page the TOC points to really starts that chapter
    pages = text_pages(pdf)
    assert "Your First Loaf" in pages[int(rows["Your First Loaf"]) - 1]
    # no leftover pass-1 markers, and the outline (bookmarks) exists
    assert not any("@@EF:" in t for t in pages)
    assert len(reader.outline) >= 2


def test_phone_edition_is_smaller(demo):
    full = demo / "dist" / "sourdough-basics.pdf"
    phone = demo / "dist" / "sourdough-basics-phone.pdf"
    assert phone.exists() and phone.stat().st_size < full.stat().st_size
    assert len(PdfReader(str(phone)).pages) == len(PdfReader(str(full)).pages)


def test_sampler_and_assets(demo):
    run("sampler", "--book", str(demo), "--chapters", "1")
    s = demo / "dist" / "sourdough-basics-sampler.pdf"
    txt = "\n".join(text_pages(s))
    assert "Get the full book" in txt and "example.gumroad.com/l/sourdough-basics" in txt
    assert "Your First Loaf" in txt  # listed on the CTA page, not included as a chapter
    run("assets", "--book", str(demo))
    from PIL import Image
    a = demo / "dist" / "assets"
    assert Image.open(a / "cover-1280x720.jpg").size == (1280, 720)
    assert Image.open(a / "thumb-600x600.jpg").size == (600, 600)
    assert Image.open(a / "carousel-01.jpg").size == (1080, 1350)
    assert Image.open(a / "pin-01.jpg").size == (1000, 1500)


def test_init_korean_book(tmp_path):
    book = tmp_path / "my-book"
    run("init", str(book))
    cfg = (book / "book.yaml").read_text().replace("language: en", "language: ko")
    (book / "book.yaml").write_text(cfg)
    (book / "chapters" / "02-ko.md").write_text(
        "# 한국어 장\n\n첫 문단은 리드 문장이 됩니다.\n\n## 준비물\n\n- [ ] 물 2리터\n\n> [!WARNING]\n> 가스 밸브를 잠그세요.\n",
        encoding="utf-8")
    run("build", "--book", str(book), "--no-phone")
    pdf = next((book / "dist").glob("*.pdf"))
    txt = "\n".join(text_pages(pdf))
    assert "차례" in txt and "한국어 장" in txt and "2장" in txt and "주의" in txt


def test_bad_chapter_selection(demo):
    r = subprocess.run([sys.executable, "-m", "ebookfactory", "sampler", "-b", str(demo), "-c", "1,3"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2 and "out of range" in r.stderr
