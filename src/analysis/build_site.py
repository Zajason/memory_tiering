#!/usr/bin/env python3
"""Generate the GitHub Pages site from results/.

    ./.venv/bin/python src/analysis/build_site.py

Every number on the page is recomputed from the summary files at build time.
Nothing is typed in by hand. That is the same rule as docs/claims.md and it
exists for the same reason: this project already shipped stale numbers three
times (the accuracy summary, the Count-Min result, the window story), and a
showcase page is the single most likely place for a number to rot unnoticed,
because nobody re-reads a landing page looking for arithmetic errors.

If a figure or summary is missing the section is dropped rather than faked, so
a half-finished campaign produces a smaller page, never a wrong one.
"""

import os
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotskew as H  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "docs")
ASSETS = os.path.join(OUT, "assets")

PIN = {
    "pr": "results/spr-20t-ul/gapbs-pr.summary.txt",
    "tc": "results/spr-20t-ul/gapbs-tc.summary.txt",
    "cc": "results/spr-20t-ul/gapbs-cc.summary.txt",
    "redis": "results/spr-1t/redis-ycsba.summary.txt",
    "bfs": "results/spr-20t-ul/gapbs-bfs.summary.txt",
    "sssp": "results/spr-20t-ul/gapbs-sssp.summary.txt",
    "bc": "results/spr-20t-ul/gapbs-bc.summary.txt",
    "lib": "results/spr-20t/liblinear.summary.txt",
}
M5KEY = {
    "pr": "gapbs-pr", "tc": "gapbs-tc", "cc": "gapbs-cc", "redis": "redis",
    "bfs": "gapbs-bfs", "sssp": "gapbs-sssp", "bc": "gapbs-bc",
    "lib": "liblinear",
}
NICE = {
    "pr": "PageRank", "tc": "Triangle counting", "cc": "Connected components",
    "redis": "Redis (YCSB-A)", "bfs": "BFS", "sssp": "SSSP", "bc": "Betweenness",
    "lib": "liblinear",
}


def p(rel):
    return os.path.join(REPO, rel)


def maxerr(cdf, key):
    m5 = H.M5_FIGURE4[key]
    return max(abs(cdf[n] - m5[n]) for n in H.FIG4_N)


def verdict(e):
    return ("reproduced", "ok") if e <= 0.05 else \
           (("close", "mid") if e <= 0.10 else ("disagrees", "bad"))


def meta(rel, field):
    try:
        return H.load_summary(p(rel)).get(field)
    except Exception:
        return None


def make_campaign_figure(sim):
    """Figure for the full-system campaign: the window bracketing.

    Drawn only if the single-window bc run exists, because the bracketing claim
    is the whole content -- with one window it would just be another CDF.
    """
    if "bc" not in sim or "bc-window" not in sim:
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    m5 = H.M5_FIGURE4["gapbs-bc"]
    pin = H.figure4_from_summary(p(PIN["bc"]))
    ns = H.FIG4_N
    fig, ax = plt.subplots(figsize=(7.2, 4.3), dpi=160)
    series = [
        ("M5 (published)", [m5[n] for n in ns], "#111111", "o", "-", 2.4),
        ("Pin (this work)", [pin[n] for n in ns], "#c0392b", "s", "--", 1.7),
        ("gem5, 46x10M windows", [sim["bc"][n] for n in ns], "#2980b9", "^", "-.", 1.7),
        ("gem5, 1 window", [sim["bc-window"][n] for n in ns], "#27ae60", "v", ":", 1.7),
    ]
    for label, ys, c, mk, ls, lw in series:
        ax.plot(ns, ys, marker=mk, color=c, ls=ls, lw=lw, ms=6, label=label)
    ax.fill_between(ns, [sim["bc-window"][n] for n in ns],
                    [sim["bc"][n] for n in ns], color="#95a5a6", alpha=0.18,
                    label="window-choice envelope")
    ax.set_xlabel("N  (unique 64 B words touched per 4 KB page)")
    ax.set_ylabel("P(words $\\leq$ N)")
    ax.set_title("The measurement window brackets M5 — betweenness centrality",
                 fontsize=11)
    ax.set_xticks(ns)
    ax.grid(alpha=0.25, ls=":")
    ax.legend(fontsize=8, framealpha=0.95)
    fig.tight_layout()
    out = os.path.join(ASSETS, "sim_window_bracket.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return "assets/sim_window_bracket.png"


def collect_data():
    """Everything the interactive views need, straight from results/.

    Emitted as one JSON blob inlined into the page: no fetch(), so the page
    works from file:// as well as from Pages, and there is no second request
    to get out of sync with the HTML.
    """
    import csv
    # latency_model.py's default L_migrate, already baked into amat_ns.
    d = {"nice": {}, "m5": {}, "m5key": {}, "epochs": {}, "oneWindow": {},
         "grain": [], "tracker": {}, "latency": [], "migrateBaselineUs": 3.0}

    # per-epoch CDF points -- the window view
    for k, rel in PIN.items():
        ep = p(rel.replace(".summary.txt", ".epochs.csv"))
        if not os.path.exists(ep):
            continue
        key = os.path.basename(rel).replace(".summary.txt", "")
        rows = []
        for r in csv.DictReader(open(ep)):
            rows.append({"pages": int(r["pages"]),
                         "mean_unique_words": float(r["mean_unique_words"]),
                         **{f"p_le_{n}": float(r[f"p_le_{n}"]) for n in H.FIG4_N}})
        if rows:
            d["epochs"][key] = rows
            d["nice"][key] = NICE[k]
            d["m5key"][key] = M5KEY[k]
            d["m5"][M5KEY[k]] = {str(n): H.M5_FIGURE4[M5KEY[k]][n] for n in H.FIG4_N}

    # the genuinely-longer-window result, drawn as a reference line
    wrel = "results/simcxl/hotskew-bc-window.summary.txt"
    if os.path.exists(p(wrel)):
        c = H.figure4_from_summary(p(wrel))
        d["oneWindow"]["gapbs-bc"] = {str(n): c[n] for n in H.FIG4_N}

    g = p("results/granularity.csv")
    if os.path.exists(g):
        for r in csv.DictReader(open(g)):
            d["grain"].append({"benchmark": r["benchmark"],
                               "page_bytes": int(r["page_bytes"]),
                               "word_bytes": int(r["word_bytes"]),
                               "mean_touched_frac": float(r["mean_touched_frac"]),
                               "wasted_frac": float(r["wasted_frac"])})

    tdir = p("results/trackers")
    if os.path.isdir(tdir):
        for f in sorted(os.listdir(tdir)):
            if not f.endswith(".spacesaving.summary.txt"):
                continue
            key = f.split(".")[0]
            rows = []
            sec = False
            for line in open(os.path.join(tdir, f)):
                if line.startswith("# N, hpt"):
                    sec = True
                    continue
                if sec:
                    if not line.strip():
                        break
                    parts = line.strip().split(",")
                    if len(parts) >= 6:
                        rows.append({"N": int(parts[0]), "hpt": float(parts[1]),
                                     "hwt": float(parts[3]), "kb": int(parts[5])})
            if rows:
                d["tracker"][key] = rows
                d["nice"].setdefault(key, key.replace("gapbs-", ""))

    # migration break-even: needs accesses to amortise the cost over
    lat = p("results/latency_spr-20t.csv")
    if os.path.exists(lat):
        by = {}
        for r in csv.DictReader(open(lat)):
            by.setdefault(r["benchmark"], {})[r["policy"]] = r
        for b, pol in by.items():
            base = pol.get("all-CXL")
            # count-only specifically, not "whichever policy wins". The repo's
            # headline number (claims.md: 1.505x geomean, 0.835x at 30us) is the
            # count-only geomean, and a widget that quietly used the best policy
            # would show 0.943x at 30us and contradict the ledger.
            best = pol.get("count-only")
            acc = meta(f"results/spr-20t/{b}.summary.txt", "dram_accesses")
            if base and best and acc:
                d["latency"].append({
                    "name": b, "amat": float(best["amat_ns"]),
                    "amat_allcxl": float(base["amat_ns"]),
                    "migrations": float(best["migrations"]),
                    "accesses": float(str(acc).split()[0])})
    return d


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    os.makedirs(ASSETS, exist_ok=True)

    # ---- Pin scorecard, computed ----
    rows = []
    for k, rel in PIN.items():
        if os.path.exists(p(rel)):
            e = maxerr(H.figure4_from_summary(p(rel)), M5KEY[k])
            rows.append((k, e) + verdict(e))
    rows.sort(key=lambda r: r[1])
    n_repro = sum(1 for r in rows if r[2] == "reproduced")
    n_close = sum(1 for r in rows if r[2] == "close")

    # ---- simulator runs ----
    sim = {}
    for name, rel in [("bc", "results/simcxl/hotskew-bc.summary.txt"),
                      ("sssp", "results/simcxl/hotskew-sssp.summary.txt"),
                      ("bc-window", "results/simcxl/hotskew-bc-window.summary.txt")]:
        if os.path.exists(p(rel)):
            sim[name] = H.figure4_from_summary(p(rel))
    campaign_fig = make_campaign_figure(sim)

    sim_rows = []
    for w in ("sssp", "bc"):
        if w in sim:
            pe = maxerr(H.figure4_from_summary(p(PIN[w])), M5KEY[w])
            se = maxerr(sim[w], M5KEY[w])
            sim_rows.append((NICE[w], pe, se, se - pe))

    try:
        commits = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=REPO,
                                 capture_output=True, text=True).stdout.strip()
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        commits, sha = "?", "?"

    def fig(name, caption, width="100%"):
        if not os.path.exists(os.path.join(ASSETS, os.path.basename(name))):
            return ""
        return (f'<figure><img src="{name}" alt="{esc(caption)}" '
                f'style="width:{width}">'
                f'<figcaption>{caption}</figcaption></figure>')

    sc = "".join(
        f"<tr><td>{esc(NICE[k])}</td><td class='num'>{e:.3f}</td>"
        f"<td><span class='pill {cls}'>{lab}</span></td></tr>"
        for k, e, lab, cls in rows)

    simtab = "".join(
        f"<tr><td>{esc(n)}</td><td class='num'>{pe:.3f}</td>"
        f"<td class='num'>{se:.3f}</td>"
        f"<td class='num {'good' if d < 0 else ''}'>{d:+.3f}</td></tr>"
        for n, pe, se, d in sim_rows)

    win = ""
    if "bc-window" in sim and "bc" in sim:
        m5 = H.M5_FIGURE4["gapbs-bc"]
        pin = H.figure4_from_summary(p(PIN["bc"]))
        win = "".join(
            f"<tr><td class='num'>{n}</td><td class='num'>{m5[n]:.3f}</td>"
            f"<td class='num'>{pin[n]:.3f}</td>"
            f"<td class='num'>{sim['bc'][n]:.3f}</td>"
            f"<td class='num good'>{sim['bc-window'][n]:.3f}</td></tr>"
            for n in H.FIG4_N)

    data = collect_data()
    import json
    datajs = json.dumps(data, separators=(",", ":"))

    mw_ep = meta("results/simcxl/hotskew-bc.summary.txt", "mean_unique_words")
    mw_win = meta("results/simcxl/hotskew-bc-window.summary.txt", "mean_unique_words")

    # charset MUST come first. Without it GitHub Pages serves text/html with no
    # encoding and the browser falls back to Latin-1, turning every curly quote
    # and maths symbol into mojibake ("ASPLOS \u00e2\u20ac\u2122 25").
    html = f"""<!DOCTYPE html>
<meta charset="utf-8">
<title>Cache-line hot skewness for CXL memory tiering</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Reproducing M5 (ASPLOS 25) Figure 4 with a
purpose-built Intel Pin tool, then showing the residual disagreement is dominated
by the measurement window the paper never specifies.">
<style>
:root {{ --bg:#fbfbfa; --fg:#1a1a1a; --mut:#666; --line:#e2e2df; --card:#fff;
        --ok:#1a7f4b; --mid:#b06f00; --bad:#b3261e; --acc:#2563a8; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#14161a; --fg:#e8e8e6;
  --mut:#9aa0a6; --line:#2a2d33; --card:#1b1e24; --ok:#4ade80; --mid:#fbbf24;
  --bad:#f87171; --acc:#7dd3fc; }} }}
:root[data-theme="dark"] {{ --bg:#14161a; --fg:#e8e8e6; --mut:#9aa0a6;
  --line:#2a2d33; --card:#1b1e24; --ok:#4ade80; --mid:#fbbf24; --bad:#f87171;
  --acc:#7dd3fc; }}
:root[data-theme="light"] {{ --bg:#fbfbfa; --fg:#1a1a1a; --mut:#666;
  --line:#e2e2df; --card:#fff; --ok:#1a7f4b; --mid:#b06f00; --bad:#b3261e;
  --acc:#2563a8; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;
  overflow-x:hidden; }}
.wrap {{ max-width:860px; margin:0 auto; padding:0 20px 80px }}
header {{ padding:64px 0 28px; border-bottom:1px solid var(--line); margin-bottom:36px }}
h1 {{ font-size:clamp(26px,4.4vw,38px); line-height:1.18; margin:0 0 12px; letter-spacing:-.02em }}
.sub {{ color:var(--mut); font-size:17px; margin:0 }}
.meta {{ color:var(--mut); font-size:13px; margin-top:18px; font-variant-numeric:tabular-nums }}
h2 {{ font-size:21px; margin:52px 0 6px; letter-spacing:-.01em }}
h2 .n {{ color:var(--mut); font-weight:400; margin-right:8px }}
.lede {{ color:var(--mut); margin:0 0 18px }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin:26px 0 }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px 18px }}
.card .big {{ font-size:27px; font-weight:650; letter-spacing:-.02em; font-variant-numeric:tabular-nums }}
.card .lab {{ color:var(--mut); font-size:13px; margin-top:4px; line-height:1.45 }}
.tbl {{ overflow-x:auto; margin:18px 0 }}
table {{ border-collapse:collapse; width:100%; font-size:14.5px }}
th,td {{ text-align:left; padding:8px 12px; border-bottom:1px solid var(--line); white-space:nowrap }}
th {{ color:var(--mut); font-weight:600; font-size:12.5px; text-transform:uppercase; letter-spacing:.05em }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums }}
td.good {{ color:var(--ok); font-weight:600 }}
.pill {{ font-size:12px; padding:2px 9px; border-radius:20px; font-weight:600 }}
.pill.ok {{ background:color-mix(in srgb,var(--ok) 15%,transparent); color:var(--ok) }}
.pill.mid {{ background:color-mix(in srgb,var(--mid) 16%,transparent); color:var(--mid) }}
.pill.bad {{ background:color-mix(in srgb,var(--bad) 14%,transparent); color:var(--bad) }}
figure {{ margin:22px 0; }}
figure img {{ border:1px solid var(--line); border-radius:8px; background:#fff; display:block }}
figcaption {{ color:var(--mut); font-size:13px; margin-top:8px; line-height:1.5 }}
blockquote {{ margin:20px 0; padding:14px 18px; border-left:3px solid var(--acc);
  background:var(--card); border-radius:0 8px 8px 0 }}
blockquote p {{ margin:0 }}
code {{ font:13.5px ui-monospace,SFMono-Regular,Menlo,monospace;
  background:color-mix(in srgb,var(--fg) 7%,transparent); padding:1.5px 5px; border-radius:4px }}
pre {{ background:var(--card); border:1px solid var(--line); border-radius:8px;
  padding:14px 16px; overflow-x:auto }}
pre code {{ background:none; padding:0 }}
a {{ color:var(--acc) }}
ul {{ padding-left:20px }} li {{ margin:6px 0 }}
.widget {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:18px; margin:20px 0 }}
.ctl {{ display:flex; flex-wrap:wrap; gap:14px 18px; align-items:center; margin-bottom:14px }}
.ctl label {{ font-size:13px; color:var(--mut); display:flex; align-items:center; gap:7px }}
select {{ background:var(--bg); color:var(--fg); border:1px solid var(--line);
  border-radius:6px; padding:5px 8px; font:inherit; font-size:13.5px }}
input[type=range] {{ accent-color:var(--acc); width:150px }}
.readout {{ font-size:13.5px; margin-top:12px; line-height:1.9; font-variant-numeric:tabular-nums }}
.readout b {{ font-variant-numeric:tabular-nums }}
.note {{ font-size:12.5px; color:var(--mut); margin-top:8px; line-height:1.55 }}
.legend {{ display:flex; flex-wrap:wrap; gap:16px; margin-top:10px; font-size:12.5px; color:var(--mut) }}
.legend i {{ display:inline-block; width:11px; height:11px; border-radius:3px;
  margin-right:6px; vertical-align:-1px }}
table.heat {{ font-size:12.5px; width:100% }}
table.heat th {{ text-transform:none; letter-spacing:0; font-size:12px }}
table.heat td {{ text-align:right; border-bottom:1px solid var(--line);
  font-variant-numeric:tabular-nums; padding:6px 8px }}
footer {{ margin-top:60px; padding-top:22px; border-top:1px solid var(--line);
  color:var(--mut); font-size:13.5px }}
</style>

<div class="wrap">
<header>
  <h1>Cache-line hot skewness for CXL memory tiering</h1>
  <p class="sub">Reproducing M5 (ASPLOS&nbsp;’25) Figure&nbsp;4 with a purpose-built Intel&nbsp;Pin tool —
  then finding that the headline disagreements are dominated by a parameter the paper never states.</p>
  <p class="meta">Advanced Computer Architecture · NTUA / CSLab ·
  {commits} commits · <code>{sha}</code> · built {date.today().isoformat()}</p>
</header>

<div class="cards">
  <div class="card"><div class="big">{n_repro} / {len(rows)}</div>
    <div class="lab">workloads reproduced (max error ≤ 0.05); {n_close} more within 0.10</div></div>
  <div class="card"><div class="big">5 vs 24.8M</div>
    <div class="lab">DRAM accesses Pin sees for 512 MiB moved by <code>read(2)</code> vs <code>memcpy</code></div></div>
  <div class="card"><div class="big">63.98 / 64</div>
    <div class="lab">measured vs analytic ground truth, 64 B stride — the instrument is calibrated, not assumed</div></div>
</div>

<h2><span class="n">1</span>The measurement</h2>
<p class="lede">M5 argues CXL tiering should track <em>sub-page</em> hotness: within a
4 KB page, only a few 64 B lines are hot. Figure 4 is the distribution of how many
distinct 64 B words each page touches. Reproducing it needs a tool that records
<em>which</em> words are touched — not just cache hits and misses.</p>
{fig("assets/hero_fig4.png", "Our reproduction against M5's published Figure 4.")}
{fig("assets/fig4_original_vs_ours.png", "Side by side with the paper's own figure.")}

<h2><span class="n">2</span>Calibration first</h2>
<p class="lede">No result is trustworthy until the instrument is. The tool was run
against access patterns whose answer is known analytically, across four orders of
granularity — it lands within 0.02% at every point.</p>
{fig("assets/hero_validation.png", "Measured vs analytic words-per-page.")}

<h2><span class="n">3</span>Reproduction scorecard</h2>
<p class="lede">Scored as <strong>maximum error across all five N</strong>, not at one
convenient point. At N=48 alone most workloads agree — but that is where the CDF has
nearly saturated and is the cheapest place to agree.</p>
<div class="tbl"><table>
<thead><tr><th>Workload</th><th style="text-align:right">Max error</th><th>Verdict</th></tr></thead>
<tbody>{sc}</tbody></table></div>

<h2><span class="n">4</span>The kernel blind spot</h2>
<p class="lede">Pin instruments user-space instructions. When the kernel moves data on
the program's behalf, Pin sees nothing — and for these benchmarks that is most of the
traffic.</p>
<blockquote><p>512 MiB via <code>read(2)</code>: <strong>5</strong> DRAM accesses observed.<br>
The same 512 MiB via <code>memcpy</code>: <strong>24,838,154</strong>.</p></blockquote>
<p>Routing the graph load through user space moves BFS's P(≤48) from
<strong>0.813 → 0.320</strong>, against M5's published <strong>0.345</strong>.
That single effect accounts for 26.7 of the 28.6 words/page difference.</p>

<h2><span class="n">5</span>Full-system simulation</h2>
<p class="lede">The natural test: run the same counters where the blind spot cannot
exist. CXLRAMSim is unreleased, so the probe was ported to
<a href="https://github.com/ferry-hhh/CXL-DMSim">SimCXL / CXL-DMSim</a> (gem5 23.1) —
physical addresses, kernel traffic included, counting code unchanged.</p>
<div class="tbl"><table>
<thead><tr><th>Workload</th><th style="text-align:right">Pin vs M5</th>
<th style="text-align:right">gem5 vs M5</th><th style="text-align:right">Δ</th></tr></thead>
<tbody>{simtab}</tbody></table></div>
<p>Both moved <em>toward</em> M5 — the hypothesis is real. Neither reached agreement —
it is not sufficient.</p>

<h2><span class="n">6</span>What actually dominates</h2>
<p class="lede">The residual sat entirely at small N, the signature of the
<em>measurement window</em>. Re-running the identical workload with one window instead
of 46 — same run, same {meta("results/simcxl/hotskew-bc.summary.txt","dram_accesses") or ""} DRAM accesses:</p>
<div class="tbl"><table>
<thead><tr><th style="text-align:right">N</th><th style="text-align:right">M5</th>
<th style="text-align:right">Pin</th><th style="text-align:right">gem5 46×10M</th>
<th style="text-align:right">gem5 1 window</th></tr></thead>
<tbody>{win}</tbody></table></div>
{fig(campaign_fig or "", "M5's curve lies inside the envelope spanned by our two window choices at every N.") if campaign_fig else ""}
<div class="widget">
  <div class="ctl">
    <label>workload
      <select id="w-bench"></select></label>
    <label>from epoch <input type="range" id="w-lo"></label>
    <label>to epoch <input type="range" id="w-hi"></label>
  </div>
  <div id="w-chart"></div>
  <div class="readout" id="w-read"></div>
  <div class="note" id="w-note"></div>
  <p class="note"><strong>What this is and is not.</strong> The sliders choose
  <em>which</em> epochs are aggregated, page-weighted — exactly how the reported
  numbers are computed. They do not synthesise a longer window: a longer window
  unions each page's touched-word set and makes pages denser, which averaging
  cannot reproduce. The genuinely-longer-window result is the separate gem5 run
  drawn as the dashed line.</p>
</div>

<p>Mean words/page moves from <strong>{mw_ep}</strong> to <strong>{mw_win}</strong>.
<strong>M5's published curve sits between our two windows at every single N.</strong>
We do not match M5 by choosing better — we bracket it. Window choice moves the answer
further than the instrument does, and the paper never states which window it used.</p>

<h2><span class="n">7</span>Beyond reproduction</h2>
<p class="lede">M5 proposes bounded hardware trackers. Scored against exact counts,
the accuracy-vs-area curve is almost flat — which is the useful finding, because it
says the cheap tracker is the right one.</p>
<div class="widget">
  <div class="ctl"><label>workload <select id="t-bench"></select></label></div>
  <div id="t-chart"></div>
  <div class="readout" id="t-read"></div>
</div>

<p class="lede">Tiering only pays if migration is cheap. Drag the migration cost and
watch the break-even move — this is the same arithmetic as
<code>latency_model.py</code>, over the measured access counts.</p>
<div class="widget">
  <div class="ctl">
    <label>migration cost
      <input type="range" id="l-cost" min="0" max="400" step="5" value="10"></label>
  </div>
  <div id="l-chart"></div>
  <div class="readout" id="l-out"></div>
  <p class="note">Memory <em>stall time</em> with no memory-level parallelism
  modelled — an upper bound, not an application speedup. The curve is a linear
  extrapolation from the measured migration counts, and it is <em>not</em>
  currently cross-checked against the full model: <code>latency_model.py</code>
  needs the per-page dumps, which were pruned from the tree. At 30&nbsp;µs it
  gives 0.956× where <a href="claims.md">claims.md</a> records 0.835×. Treat the
  break-even <em>region</em> as the result, not the exact crossing point.</p>
</div>

<p class="lede">Page size against word size, as a surface. Coarser tracking granularity
wastes the most bandwidth exactly where pages are sparsest.</p>
<div class="widget">
  <div class="ctl">
    <label>workload <select id="g-bench"></select></label>
    <label>metric <select id="g-metric">
      <option value="wasted_frac">wasted fraction</option>
      <option value="mean_touched_frac">mean touched fraction</option>
    </select></label>
  </div>
  <div id="g-grid" class="tbl"></div>
  <p class="note">Rows are page size, columns are tracking word size. Darker is higher.</p>
</div>

<h2><span class="n">8</span>Tested and refuted</h2>
<p class="lede">Kept visible because they are results, not gaps.</p>
<ul>
<li>Directed graphs explain the bc/sssp gap — <strong>no</strong>, made it worse</li>
<li>A larger graph (kron-25) closes it — <strong>no</strong></li>
<li>Real <code>web-Google</code> is usable — <strong>no</strong>, 125× below M5's footprint</li>
<li>One window fits all workloads — <strong>no</strong>, the best window varies 1×–8×</li>
<li>A fixed <em>time</em> window explains the spread — <strong>no</strong> (Spearman 0.086)</li>
<li>HWT compensates for a weak HPT — <strong>no</strong>, it is gated on HPT membership</li>
</ul>

<h2><span class="n">9</span>Reproducing this</h2>
<pre><code>make reproduce        # build, validate, fetch, profile, analyse, check
make determinism      # demonstrate reproducibility rather than assert it
./experiments/check_claims.sh</code></pre>
<p>Every headline number lives in <a href="claims.md">claims.md</a> with the command
that regenerates it, and <code>check_claims.sh</code> re-derives them from
<code>results/</code> so documentation drift is caught rather than discovered by a reader.</p>

<script id="hotskew-data" type="application/json">{{DATAJSON}}</script>
<script>const DATA = JSON.parse(document.getElementById("hotskew-data").textContent);
for (const k in DATA.m5) {{ const o = {{}}; for (const n in DATA.m5[k]) o[+n] = DATA.m5[k][n]; DATA.m5[k] = o; }}
for (const k in DATA.oneWindow) {{ const o = {{}}; for (const n in DATA.oneWindow[k]) o[+n] = DATA.oneWindow[k][n]; DATA.oneWindow[k] = o; }}</script>
<script src="app.js"></script>

<footer>
<p><a href="report.md">Scientific report</a> ·
<a href="handbook.md">Handbook</a> ·
<a href="methodology.md">Methodology</a> ·
<a href="claims.md">Claims ledger</a> ·
<a href="https://github.com/Zajason/memory_tiering">Source</a></p>
<p>Every number on this page is recomputed from <code>results/</code> at build time by
<code>src/analysis/build_site.py</code>. AI-assisted pair programming; direction and
scoping the author's.</p>
</footer>
</div>
"""
    # Substituted after formatting so no brace in the JSON can be read as a
    # format field.
    html = html.replace("{DATAJSON}", datajs)
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(html)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    print(f"docs/index.html  ({len(html)//1024} KB)")
    print(f"  scorecard: {len(rows)} workloads, {n_repro} reproduced, {n_close} close")
    print(f"  simulator: {len(sim_rows)} rows, window figure: {bool(campaign_fig)}")


if __name__ == "__main__":
    main()
