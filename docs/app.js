/* Interactive views over the measured data.
 *
 * DATA is injected by src/analysis/build_site.py from results/. This file never
 * contains numbers; it only draws what it is given, so the page cannot disagree
 * with the repository.
 *
 * One honesty constraint shapes the whole window widget:
 *
 *   Aggregating per-epoch CDFs is NOT the same as measuring with a longer
 *   window. A longer window unions each page's touched-word set, so pages get
 *   monotonically denser. Averaging the per-epoch distributions does not do
 *   that -- it answers "what is the mean over these windows", not "what if the
 *   window were longer".
 *
 * So the slider selects WHICH epochs are aggregated, page-weighted, which is
 * exactly how the reported multi-window numbers are computed. It never claims
 * to synthesise a different window length. The genuinely-longer-window result
 * comes from a separate gem5 run and is drawn as a fixed reference line.
 */

const NS = [4, 8, 16, 32, 48];
const $ = (s, r = document) => r.querySelector(s);

/* ---------- tiny SVG chart helpers (no dependencies, CSP-safe) ---------- */
const SVGNS = "http://www.w3.org/2000/svg";
function el(n, a = {}) {
  const e = document.createElementNS(SVGNS, n);
  for (const k in a) e.setAttribute(k, a[k]);
  return e;
}
function css(v) {
  return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
}

function lineChart(mount, series, opts = {}) {
  mount.innerHTML = "";
  const W = mount.clientWidth || 640, H = opts.height || 300;
  const m = { t: 14, r: 12, b: 42, l: 50 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H,
                          role: "img", "aria-label": opts.label || "chart" });
  const xs = opts.xs || NS;
  const xmin = xs[0], xmax = xs[xs.length - 1];
  const X = v => m.l + ((v - xmin) / (xmax - xmin || 1)) * iw;
  const Y = v => m.t + (1 - v) * ih;

  const mut = css("--mut"), line = css("--line");
  // grid + y axis
  for (let i = 0; i <= 5; i++) {
    const v = i / 5;
    svg.appendChild(el("line", { x1: m.l, x2: m.l + iw, y1: Y(v), y2: Y(v),
      stroke: line, "stroke-dasharray": "2 3" }));
    const t = el("text", { x: m.l - 8, y: Y(v) + 4, "text-anchor": "end",
      fill: mut, "font-size": 11 });
    t.textContent = v.toFixed(1);
    svg.appendChild(t);
  }
  xs.forEach(x => {
    const t = el("text", { x: X(x), y: H - 20, "text-anchor": "middle",
      fill: mut, "font-size": 11 });
    t.textContent = x;
    svg.appendChild(t);
  });
  const xl = el("text", { x: m.l + iw / 2, y: H - 4, "text-anchor": "middle",
    fill: mut, "font-size": 11.5 });
  xl.textContent = opts.xlabel || "";
  svg.appendChild(xl);

  series.forEach(s => {
    if (!s.ys) return;
    const d = s.ys.map((y, i) => `${i ? "L" : "M"}${X(xs[i])},${Y(y)}`).join(" ");
    svg.appendChild(el("path", { d, fill: "none", stroke: s.color,
      "stroke-width": s.width || 2, "stroke-dasharray": s.dash || "",
      "stroke-linejoin": "round" }));
    s.ys.forEach((y, i) =>
      svg.appendChild(el("circle", { cx: X(xs[i]), cy: Y(y), r: s.r || 3.5,
        fill: s.color })));
  });
  mount.appendChild(svg);

  const leg = document.createElement("div");
  leg.className = "legend";
  series.filter(s => s.ys).forEach(s => {
    const i = document.createElement("span");
    i.innerHTML = `<i style="background:${s.color}"></i>${s.name}`;
    leg.appendChild(i);
  });
  mount.appendChild(leg);
}

/* ---------- 1. which window you sample ---------- */
function initWindow() {
  const sel = $("#w-bench"), a = $("#w-lo"), b = $("#w-hi");
  const chart = $("#w-chart"), read = $("#w-read"), note = $("#w-note");
  if (!sel) return;

  Object.keys(DATA.epochs).forEach(k => {
    const o = document.createElement("option");
    o.value = k;
    o.textContent = DATA.nice[k] || k;
    sel.appendChild(o);
  });
  sel.value = DATA.epochs["gapbs-bc"] ? "gapbs-bc" : Object.keys(DATA.epochs)[0];

  function bounds() {
    const n = DATA.epochs[sel.value].length;
    [a, b].forEach(s => { s.min = 0; s.max = n - 1; });
    a.value = 0; b.value = n - 1;
  }

  function draw() {
    const rows = DATA.epochs[sel.value];
    let lo = +a.value, hi = +b.value;
    if (lo > hi) [lo, hi] = [hi, lo];
    const pick = rows.slice(lo, hi + 1);

    // Page-weighted aggregate: each epoch contributes `pages` page-observations.
    // This is exactly how the reported multi-window numbers are computed.
    const tot = pick.reduce((s, r) => s + r.pages, 0) || 1;
    const ys = NS.map(n =>
      pick.reduce((s, r) => s + r.pages * r["p_le_" + n], 0) / tot);
    const words = pick.reduce((s, r) => s + r.pages * r.mean_unique_words, 0) / tot;

    const m5key = DATA.m5key[sel.value];
    const m5 = m5key ? NS.map(n => DATA.m5[m5key][n]) : null;
    const err = m5 ? Math.max(...ys.map((y, i) => Math.abs(y - m5[i]))) : null;

    const series = [];
    if (m5) series.push({ name: "M5 (published)", ys: m5, color: css("--fg"), width: 2.6 });
    series.push({ name: `Pin, epochs ${lo}–${hi}`, ys, color: "#c0392b", width: 2 });
    const oneWin = DATA.oneWindow[sel.value];
    if (oneWin)
      series.push({ name: "gem5, single window", ys: NS.map(n => oneWin[n]),
                    color: "#27ae60", width: 2, dash: "4 3" });

    lineChart(chart, series, {
      xlabel: "N  (unique 64 B words per 4 KB page)", height: 300 });

    const verdict = err == null ? "" :
      err <= 0.05 ? '<span class="pill ok">reproduced</span>' :
      err <= 0.10 ? '<span class="pill mid">close</span>' :
                    '<span class="pill bad">disagrees</span>';
    read.innerHTML =
      `<div><b>${(hi - lo + 1)}</b> of ${rows.length} epochs · ` +
      `<b>${(tot / 1e6).toFixed(2)}M</b> page-observations · ` +
      `mean <b>${words.toFixed(1)}</b>/64 words</div>` +
      (err == null ? "" :
        `<div>max error vs M5 <b>${err.toFixed(3)}</b> ${verdict}</div>`);

    const full = rows.length;
    note.textContent = (hi - lo + 1) === full
      ? "This is the number reported in the scorecard: every epoch, page-weighted."
      : "Selecting a subset of epochs is a different measurement, not a better one — " +
        "early epochs are dominated by the data load and are nearly dense, later " +
        "ones are steady-state and sparse.";
  }

  sel.addEventListener("change", () => { bounds(); draw(); });
  [a, b].forEach(s => s.addEventListener("input", draw));
  bounds(); draw();
  addEventListener("resize", draw);
}

/* ---------- 2. granularity surface ---------- */
function initGrain() {
  const sel = $("#g-bench"), met = $("#g-metric"), mount = $("#g-grid");
  if (!sel) return;
  const rows = DATA.grain;
  const benches = [...new Set(rows.map(r => r.benchmark))].sort();
  benches.forEach(b => {
    const o = document.createElement("option");
    o.value = b; o.textContent = b;
    sel.appendChild(o);
  });
  sel.value = benches.includes("bc") ? "bc" : benches[0];

  const PS = [...new Set(rows.map(r => r.page_bytes))].sort((x, y) => x - y);
  const WS = [...new Set(rows.map(r => r.word_bytes))].sort((x, y) => x - y);
  const human = b => b >= 1048576 ? (b / 1048576) + " MB"
                  : b >= 1024 ? (b / 1024) + " KB" : b + " B";

  function draw() {
    const key = met.value;
    const sub = rows.filter(r => r.benchmark === sel.value);
    const vals = sub.map(r => r[key]);
    const lo = Math.min(...vals), hi = Math.max(...vals);
    let html = '<table class="heat"><thead><tr><th></th>' +
      WS.map(w => `<th>${human(w)}</th>`).join("") + "</tr></thead><tbody>";
    PS.forEach(p => {
      html += `<tr><th>${human(p)}</th>`;
      WS.forEach(w => {
        const r = sub.find(x => x.page_bytes === p && x.word_bytes === w);
        if (!r) { html += "<td></td>"; return; }
        const t = (r[key] - lo) / (hi - lo || 1);
        // single-hue ramp: readable in both themes, no red/green confusion
        const bg = `color-mix(in srgb, var(--acc) ${(8 + t * 62).toFixed(0)}%, transparent)`;
        html += `<td style="background:${bg}" title="${human(p)} / ${human(w)}">` +
                `${r[key].toFixed(2)}</td>`;
      });
      html += "</tr>";
    });
    mount.innerHTML = html + "</tbody></table>";
  }
  sel.addEventListener("change", draw);
  met.addEventListener("change", draw);
  draw();
}

/* ---------- 3. tracker budget ---------- */
function initTracker() {
  const sel = $("#t-bench"), mount = $("#t-chart"), read = $("#t-read");
  if (!sel || !DATA.tracker) return;
  Object.keys(DATA.tracker).forEach(k => {
    const o = document.createElement("option");
    o.value = k; o.textContent = DATA.nice[k] || k;
    sel.appendChild(o);
  });
  sel.value = Object.keys(DATA.tracker)[0];

  // The summary reports integer KB, so small trackers round to "0 KB".
  const area = r => r.kb >= 1 ? `${r.kb} KB` : "<1 KB";

  function draw() {
    const rows = DATA.tracker[sel.value];
    const xs = rows.map(r => r.N);
    lineChart(mount, [
      { name: "HPT accuracy", ys: rows.map(r => r.hpt), color: "#2980b9", width: 2.2 },
      { name: "HWT accuracy", ys: rows.map(r => r.hwt), color: "#8e44ad", width: 2, dash: "4 3" },
    ], { xs, xlabel: "tracker entries N", height: 260 });
    const first = rows[0], last = rows[rows.length - 1];
    const grow = last.kb && first.kb ? (last.kb / Math.max(first.kb, 1)) : null;
    read.innerHTML =
      `N=${first.N} (${area(first)}) → <b>${first.hpt.toFixed(3)}</b> · ` +
      `N=${last.N} (${area(last)}) → <b>${last.hpt.toFixed(3)}</b>` +
      (grow ? ` · <b>${grow.toFixed(0)}×</b> the SRAM for ` +
              `<b>${((last.hpt - first.hpt) * 100).toFixed(1)}</b> points` : "");
  }
  sel.addEventListener("change", draw);
  draw();
  addEventListener("resize", draw);
}

/* ---------- 4. migration-cost break-even ---------- */
function initLatency() {
  const s = $("#l-cost"), out = $("#l-out"), mount = $("#l-chart");
  if (!s || !DATA.latency) return;

  function draw() {
    const cost_us = +s.value / 10;           // slider is in 0.1us steps
    const rows = DATA.latency;
    const xs = [], ys = [];
    let losses = 0;
    rows.forEach(r => {
      // latency_model.py amortises migration cost over the run's accesses and
      // folds it into amat_ns at its default L_migrate. Subtract that baseline
      // before adding the slider's cost, or the default is counted twice.
      const per = r.accesses ? (r.migrations * 1000) / r.accesses : 0;  // ns per us
      const amat0 = r.amat - per * DATA.migrateBaselineUs;
      const sp = r.amat_allcxl / (amat0 + per * cost_us);
      xs.push(r.name); ys.push(sp);
      if (sp < 1) losses++;
    });
    const geo = Math.exp(ys.reduce((a, v) => a + Math.log(v), 0) / ys.length);
    out.innerHTML =
      `migration cost <b>${cost_us.toFixed(1)} µs</b> → geomean stall-time speedup ` +
      `<b>${geo.toFixed(3)}×</b>` +
      (losses ? ` · <span class="pill bad">${losses} of ${ys.length} now a net loss</span>`
              : ` · <span class="pill ok">all workloads still gain</span>`);
    // simple bar chart
    mount.innerHTML = "";
    const W = mount.clientWidth || 640, H = 190, m = { t: 8, r: 8, b: 44, l: 44 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const top = Math.max(2.2, Math.ceil(Math.max(...ys) * 10) / 10);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H });
    const Y = v => m.t + (1 - v / top) * ih;
    [1, top].forEach(v => {
      svg.appendChild(el("line", { x1: m.l, x2: m.l + iw, y1: Y(v), y2: Y(v),
        stroke: v === 1 ? css("--bad") : css("--line"),
        "stroke-dasharray": v === 1 ? "5 3" : "2 3" }));
      const t = el("text", { x: m.l - 6, y: Y(v) + 4, "text-anchor": "end",
        fill: css("--mut"), "font-size": 11 });
      t.textContent = v.toFixed(1) + "×";
      svg.appendChild(t);
    });
    const bw = iw / ys.length;
    ys.forEach((v, i) => {
      const h = Math.max(1, (v / top) * ih);
      svg.appendChild(el("rect", { x: m.l + i * bw + bw * 0.18, y: m.t + ih - h,
        width: bw * 0.64, height: h, rx: 3,
        fill: v < 1 ? css("--bad") : css("--acc") }));
      const t = el("text", { x: m.l + i * bw + bw / 2, y: H - 26,
        "text-anchor": "middle", fill: css("--mut"), "font-size": 10 });
      t.textContent = xs[i].replace("gapbs-", "");
      svg.appendChild(t);
    });
    const cap = el("text", { x: m.l + iw / 2, y: H - 8, "text-anchor": "middle",
      fill: css("--mut"), "font-size": 11 });
    cap.textContent = "dashed line = break-even; below it, tiering costs more than it saves";
    svg.appendChild(cap);
    mount.appendChild(svg);
  }
  s.addEventListener("input", draw);
  draw();
  addEventListener("resize", draw);
}

addEventListener("DOMContentLoaded", () => {
  try { initWindow(); } catch (e) { console.error("window", e); }
  try { initGrain(); } catch (e) { console.error("grain", e); }
  try { initTracker(); } catch (e) { console.error("tracker", e); }
  try { initLatency(); } catch (e) { console.error("latency", e); }
});
