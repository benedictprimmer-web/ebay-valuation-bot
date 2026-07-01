#!/usr/bin/env python3
"""Render a self-contained HTML dashboard from data/scatter_history.json.

  python report.py                 # -> reports/scatter-dashboard.html
  python report.py --out foo.html

No server, no external libraries, no network: the scan data is embedded into the page
and drawn with a little inline SVG, so the file opens straight in any browser. Shows
the latest scan (ranked niches, price-range bars, low-tail edge) plus a median trend
across scans when there's more than one.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build_html(history: list[dict]) -> str:
    data = json.dumps(history)
    # The template embeds the data and renders it client-side. Braces in the JS/CSS are
    # doubled so str.format only substitutes __DATA__.
    return TEMPLATE.replace("__DATA__", data)


def main() -> int:
    p = argparse.ArgumentParser(description="valbot scatter dashboard")
    p.add_argument("--history", default=None, help="path to scatter_history.json")
    p.add_argument("--out", default=None, help="output html path")
    args = p.parse_args()

    hist_path = Path(args.history) if args.history else ROOT / "data" / "scatter_history.json"
    out_path = Path(args.out) if args.out else ROOT / "reports" / "scatter-dashboard.html"
    history = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_html(history), encoding="utf-8")
    print(f"Wrote {out_path}  ({len(history)} scan(s))")
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>valbot — niche scatter dashboard</title>
<style>
  :root { --bg:#0f1419; --panel:#1a2230; --ink:#e6edf3; --mut:#8b98a9; --line:#2b3547;
          --bar:#4c8bf5; --hi:#3fb950; --lo:#f0883e; --med:#e6edf3; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  .wrap { max-width:960px; margin:0 auto; padding:24px 16px 64px; }
  h1 { font-size:20px; margin:0 0 4px; }
  h2 { font-size:15px; color:var(--mut); font-weight:600; margin:28px 0 10px;
       text-transform:uppercase; letter-spacing:.04em; }
  .sub { color:var(--mut); font-size:13px; margin-bottom:8px; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:10px;
           padding:16px; }
  .badges { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 4px; }
  .badge { background:var(--panel); border:1px solid var(--line); border-radius:999px;
           padding:4px 12px; font-size:12px; color:var(--mut); }
  .badge b { color:var(--ink); }
  table { width:100%; border-collapse:collapse; }
  th,td { text-align:right; padding:8px 10px; border-bottom:1px solid var(--line);
          font-variant-numeric:tabular-nums; }
  th:first-child, td:first-child { text-align:left; }
  th { color:var(--mut); font-weight:600; font-size:12px; }
  tr:last-child td { border-bottom:none; }
  .q { font-weight:600; }
  .muted { color:var(--mut); }
  .edge { color:var(--lo); font-weight:600; }
  svg { display:block; width:100%; height:auto; }
  .legend { display:flex; gap:16px; color:var(--mut); font-size:12px; margin-top:8px; }
  .dot { display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:5px;
         vertical-align:middle; }
  footer { color:var(--mut); font-size:12px; margin-top:32px; }
  .empty { color:var(--mut); padding:24px; text-align:center; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Niche scatter dashboard</h1>
  <div class="sub" id="sub"></div>
  <div class="badges" id="badges"></div>

  <h2>Ranked by opportunity</h2>
  <div class="sub">Score = rel-dispersion × √n. Where sold prices differ most, scaled by how many change hands.</div>
  <div class="panel" id="scoreChart"></div>

  <h2>Price range &amp; low-tail edge</h2>
  <div class="sub">Bar spans min→max sold. Diamond = median. Orange = the gap from the low tail up to median — the arbitrage headroom.</div>
  <div class="panel" id="rangeChart"></div>
  <div class="legend">
    <span><span class="dot" style="background:var(--lo)"></span>low tail → median (edge)</span>
    <span><span class="dot" style="background:var(--bar)"></span>median → max</span>
    <span><span class="dot" style="background:var(--med)"></span>median</span>
  </div>

  <h2>Detail</h2>
  <div class="panel" id="table"></div>

  <div id="trendWrap" style="display:none">
    <h2>Median over time</h2>
    <div class="panel" id="trendChart"></div>
  </div>

  <footer id="foot"></footer>
</div>

<script>
const HISTORY = __DATA__;

const gbp = v => "£" + (v==null ? "—" : Number(v).toLocaleString("en-GB",{maximumFractionDigits:0}));
const esc = s => String(s).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));

function render() {
  if (!HISTORY.length) { document.querySelector(".wrap").innerHTML =
    '<h1>Niche scatter dashboard</h1><div class="empty">No scans yet. Run <code>python scan.py --sector cameras-lenses --mode thirdparty</code>.</div>'; return; }

  const latest = HISTORY[HISTORY.length - 1];
  const rows = (latest.rows || []).filter(r => r.n).sort((a,b)=> (b.score||0)-(a.score||0));
  const skipped = (latest.rows || []).filter(r => !r.n);

  document.getElementById("sub").textContent =
    `Sector: ${latest.sector} · scanned ${new Date(latest.scanned_at).toLocaleString("en-GB")}`;

  const badges = document.getElementById("badges");
  badges.innerHTML =
    `<span class="badge"><b>${rows.length}</b> niches with data</span>` +
    (skipped.length ? `<span class="badge"><b>${skipped.length}</b> no data (${skipped.map(s=>esc(s.query)).join(", ")})</span>` : "") +
    `<span class="badge"><b>${HISTORY.length}</b> scan(s) on record</span>`;

  drawScores(rows);
  drawRanges(rows);
  drawTable(rows, skipped);
  drawTrend();
}

function bars(rows, valueFn, colorFn, labelFn) {
  const W=760, rowH=34, padL=150, padR=60, H=rows.length*rowH+10;
  const max = Math.max(...rows.map(valueFn), 1);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
  rows.forEach((r,i)=>{
    const y=i*rowH+6, w=(W-padL-padR)*(valueFn(r)/max);
    s += `<text x="${padL-8}" y="${y+16}" fill="#e6edf3" text-anchor="end" font-size="12">${esc(r.query)}</text>`;
    s += `<rect x="${padL}" y="${y+4}" width="${Math.max(w,1)}" height="16" rx="3" fill="${colorFn(r)}"></rect>`;
    s += `<text x="${padL+Math.max(w,1)+6}" y="${y+16}" fill="#8b98a9" font-size="12">${labelFn(r)}</text>`;
  });
  return s+"</svg>";
}

function drawScores(rows) {
  document.getElementById("scoreChart").innerHTML =
    bars(rows, r=>r.score||0, ()=>"var(--bar)", r=>(r.score||0).toFixed(2));
}

function drawRanges(rows) {
  const W=760, rowH=40, padL=150, padR=70, H=rows.length*rowH+10;
  const max = Math.max(...rows.map(r=>r.max||0), 1);
  const x = v => padL + (W-padL-padR)*(v/max);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
  rows.forEach((r,i)=>{
    const y=i*rowH+rowH/2;
    s += `<text x="${padL-8}" y="${y+4}" fill="#e6edf3" text-anchor="end" font-size="12">${esc(r.query)}</text>`;
    // median -> max (blue)
    s += `<rect x="${x(r.median)}" y="${y-6}" width="${Math.max(x(r.max)-x(r.median),1)}" height="12" rx="3" fill="var(--bar)" opacity="0.55"></rect>`;
    // min -> median (orange edge)
    s += `<rect x="${x(r.min)}" y="${y-6}" width="${Math.max(x(r.median)-x(r.min),1)}" height="12" rx="3" fill="var(--lo)" opacity="0.85"></rect>`;
    // median diamond
    s += `<path d="M ${x(r.median)} ${y-9} l 6 9 l -6 9 l -6 -9 z" fill="#fff"></path>`;
    s += `<text x="${x(r.max)+6}" y="${y+4}" fill="#8b98a9" font-size="11">${gbp(r.median)} · edge ${Math.round((r.edge_pct||0)*100)}%</text>`;
    s += `<text x="${x(r.min)}" y="${y-12}" fill="#8b98a9" font-size="10">${gbp(r.min)}</text>`;
  });
  return document.getElementById("rangeChart").innerHTML = s+"</svg>";
}

function drawTable(rows, skipped) {
  let h = `<table><thead><tr><th>Niche</th><th>n</th><th>median</th><th>min</th><th>max</th>
    <th>rel-disp</th><th>edge £</th><th>edge %</th><th>score</th></tr></thead><tbody>`;
  rows.forEach(r=>{
    h += `<tr><td class="q">${esc(r.query)}</td><td>${r.n}</td><td>${gbp(r.median)}</td>
      <td class="muted">${gbp(r.min)}</td><td class="muted">${gbp(r.max)}</td>
      <td>${(r.rel_dispersion||0).toFixed(2)}</td><td class="edge">${gbp(r.edge_gbp)}</td>
      <td class="edge">${Math.round((r.edge_pct||0)*100)}%</td><td>${(r.score||0).toFixed(2)}</td></tr>`;
  });
  skipped.forEach(r=>{
    h += `<tr><td class="q">${esc(r.query)}</td><td class="muted" colspan="8">${esc(r.source||"no data")}</td></tr>`;
  });
  document.getElementById("table").innerHTML = h+"</tbody></table>";
}

function drawTrend() {
  if (HISTORY.length < 2) return;
  document.getElementById("trendWrap").style.display = "block";
  const queries = [...new Set(HISTORY.flatMap(s=>(s.rows||[]).filter(r=>r.n).map(r=>r.query)))];
  const times = HISTORY.map(s=>new Date(s.scanned_at).getTime());
  const t0=Math.min(...times), t1=Math.max(...times);
  const allMed = HISTORY.flatMap(s=>(s.rows||[]).filter(r=>r.n).map(r=>r.median));
  const mMax=Math.max(...allMed,1);
  const W=760,H=240,padL=50,padR=120,padB=24,padT=10;
  const X=t=> padL+(W-padL-padR)*((t-t0)/((t1-t0)||1));
  const Y=v=> padT+(H-padT-padB)*(1-v/mMax);
  const colors=["#4c8bf5","#3fb950","#f0883e","#a371f7","#e6edf3","#db61a2"];
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img">`;
  queries.forEach((q,qi)=>{
    const pts=HISTORY.map((scan,si)=>{const r=(scan.rows||[]).find(r=>r.query===q&&r.n);return r?[X(times[si]),Y(r.median)]:null;}).filter(Boolean);
    if(!pts.length) return;
    const c=colors[qi%colors.length];
    s+=`<polyline points="${pts.map(p=>p.join(",")).join(" ")}" fill="none" stroke="${c}" stroke-width="2"></polyline>`;
    pts.forEach(p=>s+=`<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="${c}"></circle>`);
    const last=pts[pts.length-1];
    s+=`<text x="${last[0]+6}" y="${last[1]+4}" fill="${c}" font-size="11">${esc(q)}</text>`;
  });
  document.getElementById("trendChart").innerHTML=s+"</svg>";
}

render();
document.getElementById("foot").textContent =
  "Generated from data/scatter_history.json · read-only, spends no pulls.";
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
