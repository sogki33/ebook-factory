"""Free lead-magnet sampler: selected chapters + a call-to-action page (Pro)."""
from __future__ import annotations

import html

from ..builder import Extra, Renderer, _data_uri_qr, build_pdf, load_chapters
from ..config import Book, ConfigError

TEXT = {
    "en": {"label": "Next", "title": "Get the full book", "tag": "Free sampler",
           "lead": "You just read {k} of {n} chapters. The full edition includes:",
           "in": "included in this sampler", "btn": "Get the full book",
           "share": "Found this useful? Forward this free PDF to a friend — it's yours to share."},
    "ko": {"label": "다음", "title": "전체 책 받기", "tag": "무료 맛보기",
           "lead": "전체 {n}개 장 가운데 {k}개 장을 읽으셨습니다. 정식판에는 다음 내용이 들어 있습니다.",
           "in": "이 맛보기에 포함", "btn": "정식판 보러 가기",
           "share": "도움이 되셨다면 이 무료 PDF를 가족·친구에게 공유해 주세요."},
}


def parse_selection(spec: str | None, total: int, default=None) -> list[int]:
    if not spec:
        sel = list(default or [1])
    else:
        sel = []
        for part in str(spec).split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                sel.extend(range(int(a), int(b) + 1))
            else:
                sel.append(int(part))
    bad = [n for n in sel if n < 1 or n > total]
    if bad:
        raise ConfigError(f"--chapters {bad} out of range: the book has {total} chapter(s)")
    return sorted(set(sel))


def cta_html(book: Book, all_chapters, picked: set[int]) -> str:
    T = TEXT.get(book.language.split("-")[0], TEXT["en"])
    e = html.escape
    items = "".join(
        f'<li class="{"in" if c.n in picked else ""}"><b>{e(c.label)}</b> — {e(c.title)}'
        + (f' <i>({T["in"]})</i>' if c.n in picked else "") + "</li>"
        for c in all_chapters)
    btn = qr = ""
    if book.buy_url:
        btn = (f'<a class="btn" href="{e(book.buy_url)}">{T["btn"]} →</a>'
               f'<div class="url"><a href="{e(book.buy_url)}">{e(book.buy_url)}</a></div>')
        q = _data_uri_qr(book.buy_url)
        qr = f'<img class="qr" src="{q}" alt="QR">' if q else ""
    price = f'<div class="price">{e(str(book.price))}</div>' if book.price else ""
    return (f'<section class="ch cta" id="cta"><header class="ch-head"><!--MK--><div class="no">{T["label"]}</div>'
            f'<h1>{T["title"]}</h1><p class="lead">{e(book.title)}'
            + (f" — {e(book.subtitle)}" if book.subtitle else "") + "</p></header>"
            f'<p>{T["lead"].format(k=len(picked), n=len(all_chapters))}</p><ul>{items}</ul>'
            f'{price}{btn}{qr}<div class="box tip"><p>{T["share"]}</p></div></section>')


def build_sampler(book: Book, spec: str | None, pro: bool, rd: Renderer | None = None):
    chapters = load_chapters(book)
    sel = parse_selection(spec, len(chapters), book.sampler.get("chapters"))
    picked = [c for c in chapters if c.n in sel]
    T = TEXT.get(book.language.split("-")[0], TEXT["en"])
    if not book.buy_url:
        print("  ! book.yaml has no buy_url: the CTA page will have no link")
    extra = Extra("cta", T["label"], T["title"], cta_html(book, chapters, set(sel)))
    out = book.out / f"{book.slug}-sampler.pdf"
    tag = book.sampler.get("cover_tag") or T["tag"]

    def go(r):
        return build_pdf(r, book, picked, out, variant="phone", pro=pro, cover_tag=tag,
                         extras=[extra], watermark=not pro, subject="Free sampler")
    if rd:
        return go(rd)
    with Renderer() as r:
        return go(r)
