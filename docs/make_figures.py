#!/usr/bin/env python3
"""Generate the README's SVG figures from data/scatter_history.json (latest scan).

  python docs/make_figures.py

Writes docs/figure-edge.svg and docs/figure-range.svg — static, dependency-free SVGs
that GitHub renders inline in the README. Colours follow the dataviz palette
(blue #2a78d6 series, orange #eb6834 highlight, ink #0b0b0b/#52514e on #fcfcfb).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, SUB, SURF, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e6e5e1"
FONT = "font-family='-apple-system,Segoe UI,Roboto,sans-serif'"


def _latest_rows() -> list[dict]:
    hist = json.loads((ROOT / "data" / "scatter_history.json").read_text())
    rows = [r for r in hist[-1]["rows"] if r.get("n")]
    return rows


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;")


def figure_edge(rows: list[dict]) -> str:
    """Horizontal bars: low-tail edge (£) per niche = buy-near-min, sell-near-median."""
    rows = sorted(rows, key=lambda r: r["edge_gbp"], reverse=True)
    padL, padR, rowH, top = 150, 120, 40, 64
    W, H = 720, top + rowH * len(rows) + 20
    barW = W - padL - padR
    mx = max(r["edge_gbp"] for r in rows)
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' {FONT}>"]
    out.append(f"<rect width='{W}' height='{H}' fill='{SURF}'/>")
    out.append(f"<text x='24' y='30' fill='{INK}' font-size='18' font-weight='700'>"
               "Where the margin is — headroom from the low-tail bargain to the typical sold price</text>")
    out.append(f"<text x='24' y='50' fill='{SUB}' font-size='13'>"
               "Bar = median sold − cheapest sold (GBP). Longer = more room to buy low and resell at the norm. Real UK sold data.</text>")
    for i, r in enumerate(rows):
        y = top + i * rowH
        w = max(2, barW * r["edge_gbp"] / mx)
        out.append(f"<text x='{padL-10}' y='{y+20}' text-anchor='end' fill='{INK}' "
                   f"font-size='13' font-weight='600'>{_esc(r['query'].replace(' body',''))}</text>")
        out.append(f"<rect x='{padL}' y='{y+6}' width='{w:.1f}' height='20' rx='4' fill='{BLUE}'/>")
        out.append(f"<text x='{padL+w+8:.1f}' y='{y+20}' fill='{SUB}' font-size='12'>"
                   f"£{r['edge_gbp']:.0f}  ·  {round(r['edge_pct']*100)}%  ·  n={r['n']}</text>")
    return "\n".join(out) + "\n</svg>\n"


def figure_range(rows: list[dict]) -> str:
    """Price-range strip: min→median (orange, your headroom) then median→max (blue)."""
    rows = sorted(rows, key=lambda r: r["median"])
    padL, padR, rowH, top = 150, 60, 46, 78
    W = 720
    H = top + rowH * len(rows) + 34
    plotW = W - padL - padR
    hi = max(r["max"] for r in rows)
    x = lambda v: padL + plotW * v / hi
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' {FONT}>"]
    out.append(f"<rect width='{W}' height='{H}' fill='{SURF}'/>")
    out.append(f"<text x='24' y='30' fill='{INK}' font-size='18' font-weight='700'>"
               "How scattered each niche's sold prices are</text>")
    out.append(f"<text x='24' y='50' fill='{SUB}' font-size='13'>"
               "Each bar spans the cheapest→dearest sold. Diamond = median. Wider spread = more mispriced listings to catch.</text>")
    # legend
    out.append(f"<rect x='{padL}' y='60' width='11' height='11' rx='2' fill='{ORANGE}'/>"
               f"<text x='{padL+16}' y='70' fill='{SUB}' font-size='12'>low tail → median (headroom)</text>")
    out.append(f"<rect x='{padL+220}' y='60' width='11' height='11' rx='2' fill='{BLUE}'/>"
               f"<text x='{padL+236}' y='70' fill='{SUB}' font-size='12'>median → max</text>")
    # x gridlines
    for gv in range(0, int(hi) + 1, 100):
        gx = x(gv)
        out.append(f"<line x1='{gx:.1f}' y1='{top-4}' x2='{gx:.1f}' y2='{H-24}' stroke='{GRID}'/>")
        out.append(f"<text x='{gx:.1f}' y='{H-10}' text-anchor='middle' fill='{SUB}' font-size='11'>£{gv}</text>")
    for i, r in enumerate(rows):
        y = top + i * rowH + 12
        out.append(f"<text x='{padL-10}' y='{y+4}' text-anchor='end' fill='{INK}' "
                   f"font-size='13' font-weight='600'>{_esc(r['query'].replace(' body',''))}</text>")
        out.append(f"<rect x='{x(r['min']):.1f}' y='{y-5}' width='{max(2,x(r['median'])-x(r['min'])):.1f}' "
                   f"height='10' rx='3' fill='{ORANGE}'/>")
        out.append(f"<rect x='{x(r['median']):.1f}' y='{y-5}' width='{max(2,x(r['max'])-x(r['median'])):.1f}' "
                   f"height='10' rx='3' fill='{BLUE}' opacity='0.55'/>")
        mxp = x(r["median"])
        out.append(f"<path d='M {mxp:.1f} {y-8} l 6 8 l -6 8 l -6 -8 z' fill='{INK}'/>")
        out.append(f"<text x='{x(r['min']):.1f}' y='{y-10}' fill='{SUB}' font-size='10'>£{r['min']:.0f}</text>")
    return "\n".join(out) + "\n</svg>\n"


def main() -> int:
    rows = _latest_rows()
    (ROOT / "docs" / "figure-edge.svg").write_text(figure_edge(rows), encoding="utf-8")
    (ROOT / "docs" / "figure-range.svg").write_text(figure_range(rows), encoding="utf-8")
    print(f"Wrote docs/figure-edge.svg and docs/figure-range.svg from {len(rows)} niches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
