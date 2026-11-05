"""Print stylesheet for the book (Chromium paged media)."""
from __future__ import annotations

from .config import DEFAULT_THEME, Book

# Named presets. "classic" is free; the rest are Pro themes.
THEMES = {
    "classic": {**DEFAULT_THEME, "font": "sans"},
    "midnight": {"accent": "#4f46e5", "dark": "#0f172a", "ink": "#0f172a", "highlight": "#818cf8", "font": "sans"},
    "sage": {"accent": "#3f6212", "dark": "#1a2e05", "ink": "#1c1917", "highlight": "#a3e635", "font": "serif"},
    "rose": {"accent": "#be123c", "dark": "#4c0519", "ink": "#1f1720", "highlight": "#fb7185", "font": "serif"},
}
FREE_THEMES = {"classic"}

SANS = '"Noto Sans", "Noto Sans CJK KR", "Noto Sans CJK JP", "Noto Sans CJK SC", sans-serif'
SERIF = '"Noto Serif", "Noto Serif CJK KR", "Noto Serif CJK JP", "Noto Serif CJK SC", serif'


def resolve_theme(book: Book, pro: bool) -> dict:
    name = book.theme if book.theme in THEMES else "classic"
    if name not in FREE_THEMES and not pro:
        name = "classic"
    t = dict(THEMES[name])
    t.update({k: v for k, v in (book.colors or {}).items() if k in DEFAULT_THEME or k == "font"})
    t["name"] = name
    return t


def book_css(book: Book, theme: dict) -> str:
    w, h = book.page_mm
    big = w > 180  # Letter / larger trims get a bigger base size
    base = 10.6 if big else 9.2
    mx = 20 if big else 13
    head_font = SERIF if theme.get("font") == "serif" else SANS
    return f"""
:root{{--accent:{theme['accent']};--dark:{theme['dark']};--ink:{theme['ink']};--hi:{theme['highlight']};
--muted:#57534e;--faint:#a8a29e;--line:#e7e5e4;--soft:#f5f5f4}}
@page{{size:{w}mm {h}mm;margin:14mm {mx}mm 16mm;
  @bottom-center{{content:counter(page);font-family:{SANS};font-size:7pt;color:#a8a29e}}}}
@page cover{{margin:0;@bottom-center{{content:none}}}}
@page front{{@bottom-center{{content:none}}}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
body{{font-family:{SANS};font-size:{base}pt;line-height:1.68;color:var(--ink);background:#fff;orphans:3;widows:3}}
:lang(ko) body,body:lang(ko),:lang(ja) body{{word-break:keep-all;line-break:strict}}
a{{color:inherit}}
:lang(ko) .ch-head .no,:lang(ja) .ch-head .no{{letter-spacing:.08em}}
.ef-mk{{position:absolute;left:0;top:0;font-size:2pt;line-height:1;color:#000}}

/* cover */
.cover{{page:cover;position:relative;width:{w}mm;height:{h - 0.4}mm;overflow:hidden;break-after:page;background:var(--dark);color:#fff}}
.cover img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.cover .shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.25) 0%,rgba(0,0,0,0) 35%,rgba(0,0,0,.35) 60%,rgba(0,0,0,.88) 100%)}}
.cover .in{{position:absolute;left:11mm;right:11mm;bottom:18mm}}
.cover .tag{{display:inline-block;background:var(--hi);color:#111;font-weight:800;font-size:8pt;padding:1.2mm 3mm;border-radius:1mm;margin-bottom:5mm;letter-spacing:.06em;text-transform:uppercase}}
.cover .title{{font-family:{head_font};font-size:{34 if big else 30}pt;line-height:1.08;font-weight:900;letter-spacing:-.02em;margin:0 0 4mm;text-shadow:0 1mm 4mm rgba(0,0,0,.5)}}
.cover .sub{{font-size:{12 if big else 10.5}pt;line-height:1.5;color:#e7e5e4;margin:0 0 6mm}}
.cover .by{{font-size:8.5pt;letter-spacing:.2em;text-transform:uppercase;color:#d6d3d1;font-weight:700}}

/* front matter */
.front{{page:front;break-after:page}}
.toc-h{{font-family:{head_font};font-size:17pt;font-weight:900;margin:2mm 0 4mm;letter-spacing:-.02em}}
.toc a{{text-decoration:none;display:flex;gap:2mm;align-items:baseline;border-bottom:.25mm dotted #d6d3d1;padding:1.5mm 0}}
.toc .c{{font-weight:800;font-size:9pt}}
.toc .c .s{{color:var(--accent);flex:0 0 17mm;font-size:8pt;letter-spacing:.04em}}
.toc .x{{font-size:8.2pt;color:var(--muted);padding:.9mm 0 .9mm 19mm}}
.toc .x .s{{flex:0 0 8mm;color:var(--faint)}}
.toc .t{{flex:1}}
.toc .p{{flex:0 0 9mm;text-align:right;font-variant-numeric:tabular-nums}}
.intro-box{{margin-top:5mm}}
.notice{{font-size:7pt;color:var(--faint);margin-top:3mm;line-height:1.55}}

/* chapters */
.ch{{break-before:page}}
.ch-head{{position:relative;background:var(--dark);color:#fafaf9;margin:0 0 5mm;padding:9mm 7mm 7mm;border-radius:2mm;overflow:hidden;break-inside:avoid}}
.ch-head:after{{content:"";position:absolute;right:-8mm;top:-8mm;width:34mm;height:34mm;border-radius:50%;border:5mm solid var(--hi);opacity:.18}}
.ch-head.has-art:after{{display:none}}
.ch-art{{height:{80 if big else 62}mm;margin:-9mm -7mm 6mm;background-size:cover;background-position:center}}
.ch-head .no{{font-size:8pt;letter-spacing:.3em;color:var(--hi);font-weight:800;text-transform:uppercase}}
.ch-head h1{{font-family:{head_font};font-size:{22 if big else 19}pt;font-weight:900;letter-spacing:-.02em;line-height:1.22;margin:2mm 0 3mm;color:#fff}}
.ch-head .lead{{color:#d6d3d1;font-size:{base - 0.4}pt;margin:0}}
.ch-head .lead b,.ch-head .lead strong{{color:#fff}}
h2{{position:relative;font-family:{head_font};font-size:{14 if big else 12.5}pt;font-weight:900;letter-spacing:-.01em;margin:6mm 0 2.5mm;line-height:1.35;break-after:avoid}}
h2 .n{{display:inline-block;background:var(--accent);color:#fff;font-family:{SANS};font-size:8pt;border-radius:1mm;padding:.2mm 1.8mm;margin-right:2mm;vertical-align:2px}}
h3{{font-size:{base + 0.8}pt;margin:4mm 0 1.5mm;color:var(--accent);break-after:avoid}}
h4{{font-size:{base}pt;margin:3mm 0 1mm;break-after:avoid}}
p{{margin-bottom:2.4mm}}
ul,ol{{margin:1mm 0 2.6mm 5mm}}
li{{margin-bottom:1mm}}
li>p{{margin-bottom:1mm}}
strong,b{{color:#0c0a09}}
code{{font-family:"DejaVu Sans Mono",monospace;font-size:.9em;background:var(--soft);padding:0 1mm;border-radius:.6mm}}
pre{{background:var(--soft);padding:3mm;border-radius:1.5mm;font-size:7.8pt;margin:2mm 0 3mm;white-space:pre-wrap;break-inside:avoid}}
pre code{{background:none;padding:0}}
hr{{border:0;border-top:.3mm solid var(--line);margin:4mm 0}}

/* figures */
.fig{{margin:2.5mm 0 3.5mm;break-inside:avoid}}
.fig img{{width:100%;max-height:{110 if big else 80}mm;object-fit:contain;border-radius:1.5mm;display:block;background:var(--soft)}}
.fig figcaption{{font-size:7.4pt;color:var(--muted);margin-top:1.4mm;line-height:1.5}}
.fig figcaption b{{color:var(--accent)}}

/* callouts */
.box{{border-radius:1.5mm;padding:2.8mm 3.6mm;margin:3mm 0;font-size:{base - 0.6}pt;break-inside:avoid;background:var(--soft);border-left:1mm solid var(--faint)}}
.box .bh{{font-weight:800;margin-bottom:1mm;font-size:{base - 0.4}pt}}
.box p:last-child,.box ul:last-child{{margin-bottom:0}}
.box.tip{{background:#eff6ff;border-color:#2563eb}}.box.tip .bh{{color:#1d4ed8}}
.box.note{{background:#f5f5f4;border-color:#78716c}}.box.note .bh{{color:#44403c}}
.box.do{{background:#ecfdf5;border-color:#059669}}.box.do .bh{{color:#047857}}
.box.dont{{background:#fef2f2;border-color:#dc2626}}.box.dont .bh{{color:#b91c1c}}
.box.warn{{background:#fffbeb;border-color:#d97706}}.box.warn .bh{{color:#b45309}}
.box.imp{{background:var(--dark);border-color:var(--hi);color:#fafaf9}}.box.imp .bh{{color:var(--hi)}}
.box.imp b,.box.imp strong{{color:#fff}}
.box a{{color:#1d4ed8;text-decoration:underline}}.box.imp a{{color:var(--hi)}}

/* tables */
table{{width:100%;border-collapse:collapse;font-size:{base - 1.3}pt;margin:2mm 0 3.5mm}}
th,td{{border-bottom:.25mm solid var(--line);padding:1.3mm 1.6mm;text-align:left;vertical-align:top}}
th{{background:var(--soft);font-weight:800}}
tr{{break-inside:avoid}}

/* checklists */
ul.checklist{{list-style:none;margin-left:0}}
li.task{{position:relative;padding:.6mm 0 .6mm 6.2mm;border-bottom:.2mm dashed var(--line);break-inside:avoid}}
li.task .cb{{position:absolute;left:0;top:1.5mm;width:3.6mm;height:3.6mm;border:.35mm solid var(--muted);border-radius:.6mm;background:#fff}}
li.task.done .cb{{background:var(--accent);border-color:var(--accent);box-shadow:inset 0 0 0 .6mm #fff}}

/* sampler CTA */
.cta{{text-align:left}}
.cta .price{{font-size:20pt;font-weight:900;color:var(--accent);margin:2mm 0}}
.cta .btn{{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;font-weight:800;padding:2.6mm 5mm;border-radius:1.5mm;margin:2mm 0 3mm}}
.cta .url{{font-size:8pt;color:var(--muted);word-break:break-all}}
.cta .qr{{width:30mm;height:30mm;margin-top:3mm}}
.cta li.in b{{color:var(--accent)}}
"""
