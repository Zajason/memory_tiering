// Generates docs/memory-tiering-cxl-gr.pptx — concept presentation (Greek)
//
// Visual paradigm: academic conference talk (LaTeX/Beamer). Serif type
// (Times New Roman), white background, numbered sections (§3.2), booktabs
// tables, captioned figures (Σχήμα N / Πίνακας N), a thin footline, and only
// two colors used like \structure{} (navy) and \alert{} (dark red).
//
// Language: technical terms in English (Latin script), the way Greek CS/ECE
// people write — tiering, granularity, bandwidth, latency, page migration,
// profiling, hot pages, workloads, cache line, etc. Prose kept punchy.
//
// ~20 slides, sized for a 30-minute talk.  Run: node scripts/make_deck.js

const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33" x 7.5"
pres.author = "el23408";
pres.title = "Memory Tiering σε συστήματα CXL";

const TOTAL = 20;

// ── Palette ──────────────────────────────────────────────────────────────────
const BG = "FFFFFF";
const INK = "1A1A1A";
const MUT = "6E6E6E";
const NAVY = "1F3A63";
const ALERT = "8C2A2A";
const RULE = "BFBFBF";
const BLK = "F0F0EE";
const BLKA = "F7ECEC";
const COLD = "DBDFE6"; // cold cells in diagrams
const SERIF = "Times New Roman";
const CODE = "Courier New";

const ML = 0.85;
const MR = 12.48;
const CW = MR - ML;
const FOOT = "Memory Tiering σε συστήματα CXL  ·  el23408";

// ── Helpers ──────────────────────────────────────────────────────────────────
function frame(n, sec, secName, ttl) {
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText(
    [
      { text: sec ? `${sec}  ` : "", options: { color: NAVY, bold: true } },
      { text: ttl, options: { color: INK, bold: true } },
    ],
    { x: ML, y: 0.42, w: CW, h: 0.6, fontFace: SERIF, fontSize: 23, margin: 0, valign: "middle" }
  );
  s.addShape(pres.ShapeType.rect, { x: ML, y: 7.04, w: CW, h: 0.008, fill: { color: RULE } });
  s.addText(FOOT, { x: ML, y: 7.1, w: 6.5, h: 0.3, fontFace: SERIF, fontSize: 9.5, color: MUT, margin: 0, valign: "middle" });
  s.addText(secName, { x: ML + 6.5, y: 7.1, w: 3.5, h: 0.3, fontFace: SERIF, fontSize: 9.5, italic: true, color: MUT, align: "center", margin: 0, valign: "middle" });
  s.addText(`${n} / ${TOTAL}`, { x: MR - 1.5, y: 7.1, w: 1.5, h: 0.3, fontFace: SERIF, fontSize: 9.5, color: MUT, align: "right", margin: 0, valign: "middle" });
  return s;
}

function booktabs(s, x, y, colW, rows, rowH, opts = {}) {
  const w = colW.reduce((a, b) => a + b, 0);
  s.addTable(rows, {
    x, y, w, colW, rowH,
    fontFace: SERIF, fontSize: opts.fs || 13.5, color: INK,
    fill: { color: BG }, border: { type: "none" },
    valign: "middle", margin: [0.05, 0.1, 0.05, 0.1],
  });
  const h0 = Array.isArray(rowH) ? rowH[0] : rowH;
  const tot = Array.isArray(rowH) ? rowH.reduce((a, b) => a + b, 0) : rowH * rows.length;
  s.addShape(pres.ShapeType.rect, { x, y, w, h: 0.022, fill: { color: INK } });
  s.addShape(pres.ShapeType.rect, { x, y: y + h0, w, h: 0.01, fill: { color: RULE } });
  s.addShape(pres.ShapeType.rect, { x, y: y + tot, w, h: 0.022, fill: { color: INK } });
}
const hb = (t) => ({ text: t, options: { bold: true } });

function caption(s, x, y, w, label, text, align = "left") {
  s.addText(
    [{ text: label + " ", options: { bold: true } }, { text: text, options: {} }],
    { x, y, w, h: 0.32, fontFace: SERIF, fontSize: 11, italic: true, color: MUT, align, margin: 0 }
  );
}

function block(s, x, y, w, h, title, body, alert) {
  s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color: alert ? BLKA : BLK } });
  s.addText(title, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.32, fontFace: SERIF, fontSize: 14, bold: true, color: alert ? ALERT : NAVY, margin: 0 });
  s.addText(body, { x: x + 0.2, y: y + 0.46, w: w - 0.4, h: h - 0.58, fontFace: SERIF, fontSize: 13, color: INK, lineSpacing: 18, margin: 0, valign: "top" });
}

// Hanging-indent itemize. items = [lead, text, height]
function itemize(s, x, y, w, items, fs = 14) {
  let yy = y;
  items.forEach(([lead, txt, h]) => {
    s.addText("–", { x, y: yy, w: 0.28, h: 0.4, fontFace: SERIF, fontSize: fs, color: NAVY, bold: true, margin: 0, valign: "top" });
    s.addText(
      [{ text: lead ? lead + " " : "", options: { bold: true } }, { text: txt, options: {} }],
      { x: x + 0.32, y: yy, w: w - 0.32, h, fontFace: SERIF, fontSize: fs, color: INK, lineSpacing: fs * 1.28, align: "left", margin: 0, valign: "top" }
    );
    yy += h;
  });
}

// ═════════════════════════════════════════════════════════════════════════════
// 01 — Title page
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("Προηγμένα Θέματα Αρχιτεκτονικής Υπολογιστών", {
    x: ML, y: 0.95, w: CW, h: 0.35, fontFace: SERIF, fontSize: 14, italic: true, color: MUT, margin: 0,
  });
  s.addText("Memory Tiering σε συστήματα CXL", {
    x: ML, y: 1.5, w: CW, h: 0.8, fontFace: SERIF, fontSize: 40, bold: true, color: INK, margin: 0,
  });
  s.addText(
    "Προσομοίωση τεχνικών memory tiering με υποστήριξη hardware, πάνω στον προσομοιωτή CXLRAMSim",
    { x: ML, y: 2.35, w: CW, h: 0.72, fontFace: SERIF, fontSize: 18, italic: true, color: NAVY, lineSpacing: 24, margin: 0 }
  );
  s.addShape(pres.ShapeType.rect, { x: ML, y: 3.18, w: CW, h: 0.014, fill: { color: RULE } });
  s.addText("Περίληψη.", { x: ML, y: 3.35, w: 2.0, h: 0.3, fontFace: SERIF, fontSize: 14, bold: true, color: INK, margin: 0 });
  s.addText(
    "Οι μνήμες CXL δίνουν φθηνή capacity πάνω από το PCIe, αλλά με ~2–3× μεγαλύτερο latency. Έτσι " +
    "προκύπτει ένα σύστημα μνήμης δύο επιπέδων (tiering). Η εργασία δείχνει, μέσα στον CXLRAMSim, γιατί " +
    "το page migration των 4 KB από το OS δεν φτάνει για να καλύψει το χάσμα απόδοσης με την τοπική DRAM, " +
    "και εξετάζει λύσεις σε hardware (M5, NeoMem, Memstrata) που κάνουν profiling μέσα στη συσκευή CXL.",
    { x: ML + 0.35, y: 3.68, w: CW - 0.35, h: 1.5, fontFace: SERIF, fontSize: 14.5, color: INK, lineSpacing: 21, align: "justify", margin: 0 }
  );
  s.addText(
    [{ text: "Keywords:  ", options: { bold: true } }, { text: "CXL · memory tiering · page migration · hardware profiling · granularity", options: { italic: true } }],
    { x: ML + 0.35, y: 5.15, w: CW - 0.35, h: 0.32, fontFace: SERIF, fontSize: 13, color: MUT, margin: 0 }
  );
  s.addShape(pres.ShapeType.rect, { x: ML, y: 5.75, w: CW, h: 0.014, fill: { color: RULE } });
  s.addText(
    [{ text: "el23408", options: { bold: true } }, { text: "   ·   Εθνικό Μετσόβιο Πολυτεχνείο   ·   Ιούλιος 2026", options: {} }],
    { x: ML, y: 5.95, w: CW, h: 0.35, fontFace: SERIF, fontSize: 14, color: INK, margin: 0 }
  );
  s.addText("github.com/Zajason/memory_tiering", { x: ML, y: 6.35, w: CW, h: 0.3, fontFace: CODE, fontSize: 11, color: MUT, margin: 0 });
  s.addNotes("30 λεπτά ομιλία. Στόχος: δείχνω ότι κατάλαβα το πρόβλημα και έχω πλάνο. Δεν έχω ακόμα αποτελέσματα, και το λέω ανοιχτά.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 02 — Agenda
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(2, "", "Περιεχόμενα", "Περιεχόμενα");
  const secs = [
    ["1.", "Κίνητρο", "γιατί CXL, και ποιο είναι το κόστος του"],
    ["2.", "Το πρόβλημα του tiering", "promotion vs demotion"],
    ["3.", "Γιατί δεν δουλεύει σήμερα", "profiling, granularity, κόστος του migration"],
    ["4.", "Pages vs lines", "το κρίσιμο trade-off — σε τι εστιάζω"],
    ["5.", "Τα σχετικά papers", "M5, NeoMem, Memstrata"],
    ["6.", "Μεθοδολογία & πλάνο", "CXLRAMSim, πείραμα, φάσεις"],
    ["7.", "Ανοιχτά ερωτήματα", "για συζήτηση"],
  ];
  secs.forEach(([n, h, d], i) => {
    const y = 1.65 + i * 0.72;
    s.addText(n, { x: ML + 0.3, y, w: 0.6, h: 0.5, fontFace: SERIF, fontSize: 20, bold: true, color: NAVY, margin: 0, valign: "middle" });
    s.addText(h, { x: ML + 1.0, y, w: 4.6, h: 0.5, fontFace: SERIF, fontSize: 18, color: INK, margin: 0, valign: "middle" });
    s.addText(d, { x: ML + 5.7, y, w: 6.2, h: 0.5, fontFace: SERIF, fontSize: 14.5, italic: true, color: MUT, margin: 0, valign: "middle" });
  });
  s.addNotes("Οδικός χάρτης. Το βάρος πέφτει στις ενότητες 4 και 5.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 03 — Motivation
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(3, "§1.1", "1. Κίνητρο", "Η μνήμη είναι το bottleneck");
  s.addText(
    "Η capacity της μνήμης ανά socket έχει κολλήσει: λίγα DIMM slots, λίγα pins στο DDR. Για παραπάνω " +
    "μνήμη πρέπει να πάρεις κι άλλους επεξεργαστές που δεν σου χρειάζονται. Το CXL το σπάει αυτό: βάζεις " +
    "μνήμη πάνω από το PCIe, ανεξάρτητα από τα cores.",
    { x: ML, y: 1.45, w: CW, h: 1.1, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );
  block(s, ML, 2.9, CW, 1.35, "Το νούμερο — stranded μνήμη",
    "Σε μεγάλα cloud datacenters, ~25% της DRAM μένει αχρησιμοποίητο (stranded), γιατί τα cores του " +
    "μηχανήματος έχουν ήδη νοικιαστεί σε άλλους. Το CXL στοχεύει ακριβώς σε αυτή τη χαμένη capacity " +
    "(Azure — Pond, ASPLOS ’23).");
  s.addText("Το κίνητρο είναι η φθηνή, κοινή capacity. Το κόστος είναι το latency — το βλέπουμε στην επόμενη διαφάνεια.",
    { x: ML, y: 4.6, w: CW, h: 0.6, fontFace: SERIF, fontSize: 15, italic: true, color: MUT, lineSpacing: 22, margin: 0 });
  s.addNotes("Ένα νούμερο να μείνει: ~25% stranded DRAM.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 04 — What CXL costs
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(4, "§1.2", "1. Κίνητρο", "Το κόστος: το latency της CXL");
  caption(s, ML, 1.4, 6.7, "Πίνακας 1:", "τυπικές τιμές latency και bandwidth ανά διαδρομή.");
  booktabs(s, ML, 1.75, [2.9, 2.0, 1.8], [
    [hb("Διαδρομή"), hb("Latency"), hb("Bandwidth")],
    ["Τοπική DDR5", { text: "80–100 ns", options: { fontFace: CODE, fontSize: 12 } }, "30–50 GB/s"],
    ["Άλλο NUMA socket", { text: "140–180 ns", options: { fontFace: CODE, fontSize: 12 } }, "—"],
    [{ text: "CXL (x8 Gen5)", options: { bold: true } }, { text: "250–400 ns", options: { fontFace: CODE, fontSize: 12, bold: true, color: ALERT } }, { text: "25–30 GB/s", options: { bold: true } }],
  ], [0.42, 0.42, 0.42, 0.42]);
  s.addText(
    [
      { text: "Το latency είναι ", options: {} },
      { text: "2–3× μεγαλύτερο", options: { bold: true, color: ALERT } },
      { text: " από την τοπική DDR, παρόλο που η DRAM πάνω στην κάρτα είναι κοινή DDR5. Το κόστος το βάζει το interconnect, όχι η μνήμη. Οπότε τα latency-bound workloads (pointer chasing) υποφέρουν· τα bandwidth-bound σχεδόν δεν το καταλαβαίνουν.", options: {} },
    ],
    { x: ML, y: 3.9, w: 6.7, h: 1.7, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 23, align: "justify", margin: 0 }
  );
  const fx = 8.15, fw = CW - (fx - ML);
  s.addText("Διαδρομή ενός load με LLC miss:", { x: fx, y: 1.4, w: fw, h: 0.32, fontFace: SERIF, fontSize: 13.5, italic: true, color: INK, margin: 0 });
  ["Core  →  LLC miss", "CXL Root Complex", "packetization (M2S)", "PCIe link (SERDES)", "device controller  →  de-packetize", "DRAM στην κάρτα", "και όλη η διαδρομή πίσω (S2M)"].forEach((t, i) => {
    const y = 1.85 + i * 0.42;
    s.addText(`(${i + 1})`, { x: fx, y, w: 0.5, h: 0.32, fontFace: CODE, fontSize: 12, color: NAVY, margin: 0, valign: "middle" });
    s.addText(t, { x: fx + 0.55, y, w: fw - 0.55, h: 0.32, fontFace: SERIF, fontSize: 14, color: i === 6 ? MUT : INK, italic: i === 6, margin: 0, valign: "middle" });
  });
  caption(s, fx, 4.98, fw, "Σχήμα 1:", "κάθε στάδιο προσθέτει latency· κυριαρχεί το interconnect.");
  s.addNotes("Η DRAM στην κάρτα είναι κανονική DDR5. Το interconnect είναι ο φόρος — γι' αυτό υπάρχει tiering.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 05 — The tiering problem
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(5, "§2", "2. Το πρόβλημα", "Το πρόβλημα του tiering");
  s.addText(
    "Δύο tiers μνήμης: ένα γρήγορο και μικρό (τοπική DDR) κι ένα αργό και μεγάλο (CXL). Θέλουμε τα hot " +
    "data στο γρήγορο tier. Αν το πετύχεις, ένα μηχάνημα με 25% τοπική DRAM τρέχει σχεδόν σαν να είχε 100%.",
    { x: ML, y: 1.45, w: CW, h: 0.75, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );
  const bw = (CW - 0.4) / 2;
  block(s, ML, 2.4, bw, 1.5, "Promotion  (αργό → γρήγορο)",
    "Πρέπει να γίνει στην ώρα του. Αν ένα page προαχθεί αφού έχει κρυώσει, είναι χαμένος κόπος.");
  block(s, ML + bw + 0.4, 2.4, bw, 1.5, "Demotion  (γρήγορο → αργό)",
    "Πρέπει να είναι ασφαλής. Αν κατεβάσεις ένα page που είναι ακόμα hot, ξεκινάει ping-pong.");
  s.addText(
    [
      { text: "Το demotion είναι εύκολο: ένα LRU αρκεί, και το Linux ήδη έχει LRU. ", options: {} },
      { text: "Το promotion είναι το δύσκολο —", options: { bold: true, color: ALERT } },
      { text: " πρέπει να ξέρεις ότι ένα page είναι hot τώρα, κι αυτό κοστίζει. Το λέει και η ίδια η κοινότητα του Linux MM.", options: {} },
    ],
    { x: ML, y: 4.15, w: CW, h: 1.0, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );
  s.addText("Οι τρεις επόμενες διαφάνειες: γιατί το promotion δεν δουλεύει καλά σήμερα.",
    { x: ML, y: 5.35, w: CW, h: 0.4, fontFace: SERIF, fontSize: 14, italic: true, color: MUT, margin: 0 });
  s.addNotes("Γιατί δύσκολο το promotion: πρέπει να ξέρεις ότι ένα page είναι hot ΤΩΡΑ.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 06 — Failure mode 1: profiling
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(6, "§3.1", "3. Γιατί δεν δουλεύει", "Γιατί δεν δουλεύει: το profiling");
  caption(s, ML, 1.4, CW, "Πίνακας 2:", "τρόποι εντοπισμού των hot pages και το βασικό πρόβλημα του καθενός.");
  booktabs(s, ML, 1.75, [2.6, 4.0, 5.03], [
    [hb("Μηχανισμός"), hb("Πώς δουλεύει"), hb("Βασικό πρόβλημα")],
    [{ text: "PTE-scan (DAMON)", options: { fontFace: CODE, fontSize: 11.5 } }, "Σαρώνει τα access bits των PTE", "1 bit = ναι/όχι. Το scan κρατάει δευτερόλεπτα, οπότε το hot set έχει ήδη αλλάξει"],
    [{ text: "hint faults (AutoNUMA, TPP)", options: { fontFace: CODE, fontSize: 11 } }, "Κάνει unmap τα PTE ώστε το access να πέσει σε fault", { text: "Μετράει TLB misses, όχι LLC misses — δεν συσχετίζονται καλά", options: { color: ALERT } }],
    [{ text: "PEBS / IBS (Memtis)", options: { fontFace: CODE, fontSize: 11.5 } }, "Sampling του PMU πάνω σε LLC misses", "Overhead ανάλογο του sampling rate: >50% slowdown σε πυκνό sampling"],
    [{ text: "hardware μέσα στην CXL", options: { fontFace: CODE, fontSize: 11.5, color: NAVY, bold: true } }, { text: "Counters μέσα στον controller της συσκευής", options: { color: NAVY } }, { text: "Σωστό event, μηδέν κόστος CPU — αλλά θέλει καινούριο hardware", options: { color: NAVY, bold: true } }],
  ], [0.42, 0.7, 0.7, 0.7, 0.62]);
  s.addText(
    [
      { text: "Το σημαντικό. ", options: { bold: true, color: ALERT } },
      { text: "AutoNUMA/TPP μετράνε TLB misses, αλλά το traffic προς την CXL το καθορίζουν τα LLC misses. Ένα page μπορεί να είναι πολύ hot στο TLB και σχεδόν αόρατο στην CXL. Δηλαδή βελτιστοποιούν το λάθος σήμα.", options: {} },
    ],
    { x: ML, y: 5.55, w: CW, h: 1.0, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 22, align: "justify", margin: 0 }
  );
  s.addNotes("accuracy × timeliness × overhead — διάλεξε δύο.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 07 — Failure mode 2: granularity
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(7, "§3.2", "3. Γιατί δεν δουλεύει", "Γιατί δεν δουλεύει: το granularity");
  s.addText(
    "Μέσα σε ένα page 4 KB, τα accesses δεν είναι μοιρασμένα ομοιόμορφα. Ένα lookup σε hash table αγγίζει " +
    "64 bytes από τα 4096. Το 4 KB είναι λάθος unit και προς τις δύο μεριές.",
    { x: ML, y: 1.42, w: CW, h: 0.75, fontFace: SERIF, fontSize: 15.5, color: INK, lineSpacing: 23, align: "justify", margin: 0 }
  );
  const cols = [["64 B", "cache line", "ελάχιστο waste· τα metadata εκτοξεύονται"], ["4 KB", "default του Linux", "μέτριο και στα δύο: waste και κόστος"], ["2 MB", "huge page", "φθηνό migration· τεράστιο waste (>99%)"]];
  const cwv = (CW - 1.0) / 3;
  cols.forEach((c, i) => {
    const x = ML + i * (cwv + 0.5);
    s.addText(c[0], { x, y: 2.35, w: cwv, h: 0.5, fontFace: SERIF, fontSize: 28, bold: true, color: NAVY, align: "center", margin: 0 });
    s.addText(c[1], { x, y: 2.9, w: cwv, h: 0.28, fontFace: CODE, fontSize: 11, color: MUT, align: "center", margin: 0 });
    s.addText(c[2], { x, y: 3.22, w: cwv, h: 0.6, fontFace: SERIF, fontSize: 12.5, italic: true, color: INK, align: "center", lineSpacing: 16, margin: 0 });
    if (i < 2) s.addText("−→", { x: x + cwv, y: 2.35, w: 0.5, h: 0.5, fontFace: SERIF, fontSize: 20, color: MUT, align: "center", valign: "middle", margin: 0 });
  });
  caption(s, ML, 3.95, CW, "Σχήμα 2:", "το φάσμα του granularity — καμία επιλογή δεν είναι καλή και στα δύο ταυτόχρονα.", "center");
  block(s, ML, 4.5, CW, 1.65, "Το ουσιαστικό — δεν υπάρχει PTE για cache line",
    "Άρα δεν γίνεται να κάνεις migrate cache lines αντί για pages μέσα από το OS. Ή βάζεις hardware " +
    "indirection (η τοπική DRAM γίνεται cache γραμμών), ή —κι εδώ στοχεύω— κάνεις profiling σε λεπτό " +
    "granularity (64 B) και migration σε χοντρό (4 KB). Το profiling granularity δεν είναι ίδιο με του " +
    "migration· αυτό ακριβώς κάνει το M5. Το σκάβουμε στην επόμενη ενότητα.", true);
  s.addNotes("profiling granularity ≠ migration granularity. Το M5 profiling στα 64 B, migration στα 4 KB.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 08 — Failure mode 3: migration cost
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(8, "§3.3", "3. Γιατί δεν δουλεύει", "Γιατί δεν δουλεύει: το κόστος του migration");
  s.addText("Για να προαχθεί ένα page 4 KB, το OS πληρώνει τέσσερα κόστη:", { x: ML, y: 1.42, w: CW, h: 0.35, fontFace: SERIF, fontSize: 16, color: INK, margin: 0 });
  itemize(s, ML, 1.95, 7.0, [
    ["Copy.", "4 KB read από CXL + 4 KB write σε DDR — τρώει το bandwidth που θέλεις να γλιτώσεις.", 0.62],
    ["Ενημέρωση page table.", "Διάσχιση του rmap για κάθε PTE που δείχνει στο page.", 0.5],
    ["TLB shootdown.", "IPI σε κάθε core με cached translation — συνήθως το πιο ακριβό.", 0.62],
    ["Lock contention.", "mmap_lock, LRU locks· δεν κάνει καλό scaling.", 0.5],
  ], 14);
  block(s, 8.05, 1.95, CW - (8.05 - ML), 3.15, "Τάξη μεγέθους",
    "Ένα migration ενός page κοστίζει μsec — χιλιάδες φορές πάνω από τα ~250 ns που προσπαθείς να " +
    "αποφύγεις ανά access.\n\nΆρα ένα page πρέπει να ξαναχρησιμοποιηθεί πολλές φορές για να αξίζει το " +
    "migration. Γι’ αυτό ένα λάθος promotion δεν είναι απλώς άχρηστο· είναι και επιζήμιο.");
  s.addText("Γι' αυτό κάθε σύστημα βάζει quota στο migration bandwidth και hysteresis στις αποφάσεις.",
    { x: ML, y: 5.45, w: CW, h: 0.5, fontFace: SERIF, fontSize: 14.5, italic: true, color: MUT, lineSpacing: 21, margin: 0 });
  s.addNotes("μsec έναντι ns. Χιλιαπλάσιο κόστος. Ένα λάθος promotion είναι επιζήμιο.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 09 — Pages vs lines: the cost / internal fragmentation
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(9, "§4.1", "4. Pages vs lines", "Pages vs lines: πόσο κοστίζει το page migration");
  s.addText(
    "Ας το ποσοτικοποιήσουμε. Ένα page 4 KB = 64 γραμμές των 64 B. Σε ένα τυπικό skewed workload, " +
    "μόνο λίγες γραμμές είναι πραγματικά hot· οι υπόλοιπες τις σέρνεις μαζί χωρίς λόγο.",
    { x: ML, y: 1.42, w: 6.7, h: 0.95, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 22, align: "justify", margin: 0 }
  );
  itemize(s, ML, 2.5, 6.7, [
    ["Internal fragmentation.", "Κάνεις migrate 4096 B για να σώσεις ~256 B. Το ~94% του transfer είναι κρύο.", 0.62],
    ["Κάψιμο fast-tier frame.", "Μια θέση στο γρήγορο tier πάει σε δεδομένα ~5% χρήσιμα, αντί σε μια γεμάτη-hot page.", 0.62],
    ["Migration efficiency.", "= useful bytes ÷ moved bytes. Για page migration σε skewed workload βγαίνει πολύ χαμηλό.", 0.62],
    ["Με 2 MB huge pages.", "Το waste γίνεται >99.99%. Τα huge pages λύνουν το κόστος, χειροτερεύουν το waste.", 0.62],
  ], 13.5);
  // Σχήμα 3: 8x8 grid = one page; a few hot cells
  const gx = 8.35, gy = 2.05, cell = 0.4, gap = 0.05;
  const hot = new Set([9, 10, 27, 52]);
  s.addText("1 page = 64 × 64 B lines", { x: gx, y: 1.55, w: 8 * cell + 7 * gap, h: 0.3, fontFace: SERIF, fontSize: 12.5, italic: true, color: INK, align: "center", margin: 0 });
  for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) {
    const idx = r * 8 + c;
    s.addShape(pres.ShapeType.rect, { x: gx + c * (cell + gap), y: gy + r * (cell + gap), w: cell, h: cell, fill: { color: hot.has(idx) ? NAVY : COLD } });
  }
  const gyb = gy + 8 * (cell + gap) + 0.05;
  s.addText([{ text: "■ ", options: { color: NAVY } }, { text: "hot (4 γραμμές)    ", options: {} }, { text: "■ ", options: { color: COLD } }, { text: "cold (60)", options: {} }],
    { x: gx, y: gyb, w: 8 * cell + 7 * gap, h: 0.3, fontFace: SERIF, fontSize: 12, color: INK, align: "center", margin: 0 });
  caption(s, gx, gyb + 0.32, 8 * cell + 7 * gap, "Σχήμα 3:", "migrate = 4096 B, useful ≈ 256 B → ~94% waste.", "center");
  s.addNotes("Money slide του granularity. Το access-density CDF (Σχήμα 7) θα το μετρήσει στην πράξη.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 10 — Line caching: the hardware alternative
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(10, "§4.2", "4. Pages vs lines", "Line caching: η hardware εναλλακτική");
  s.addText(
    "Η άλλη λύση: μην κάνεις migrate καθόλου με το OS. Κάνε την τοπική DRAM ένα hardware cache 64 B " +
    "γραμμών μπροστά από την CXL (near-memory cache — π.χ. Intel Flat Memory Mode).",
    { x: ML, y: 1.42, w: CW, h: 0.75, fontFace: SERIF, fontSize: 15.5, color: INK, lineSpacing: 23, align: "justify", margin: 0 }
  );
  itemize(s, ML, 2.3, 6.5, [
    ["Transparent στο OS.", "Καθόλου page faults, καθόλου TLB shootdowns, καθόλου migration daemon.", 0.55],
    ["Line granularity.", "Μετακινείς 64 B, όχι 4 KB. Το waste μηδενίζεται.", 0.5],
    ["Direct-mapped, 1:1.", "Κάθε CXL γραμμή έχει μία μόνο θέση στην DRAM. Miss → swap.", 0.5],
    ["Το κόστος:", "tag array (τεράστιο), και conflict misses όταν δύο hot γραμμές πέφτουν στην ίδια θέση.", 0.62],
  ], 13.5);
  // small direct-mapped schematic on the right
  const bx = 7.6;
  s.addShape(pres.ShapeType.rect, { x: bx, y: 2.35, w: 1.5, h: 2.6, fill: { color: BLK } });
  s.addText("CXL\n(αργή, μεγάλη)", { x: bx, y: 2.42, w: 1.5, h: 0.6, fontFace: SERIF, fontSize: 11.5, italic: true, color: INK, align: "center", margin: 0 });
  const cyA = 3.35, cyB = 4.35;
  s.addShape(pres.ShapeType.rect, { x: bx + 0.2, y: cyA, w: 1.1, h: 0.34, fill: { color: NAVY } });
  s.addText("line A", { x: bx + 0.2, y: cyA, w: 1.1, h: 0.34, fontFace: CODE, fontSize: 11, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: bx + 0.2, y: cyB, w: 1.1, h: 0.34, fill: { color: ALERT } });
  s.addText("line B", { x: bx + 0.2, y: cyB, w: 1.1, h: 0.34, fontFace: CODE, fontSize: 11, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  // DRAM slot
  const dx = 11.0, sy = 3.85;
  s.addShape(pres.ShapeType.rect, { x: dx, y: 2.9, w: 1.4, h: 1.5, fill: { color: BLK } });
  s.addText("τοπική DRAM\n(cache)", { x: dx, y: 2.96, w: 1.4, h: 0.5, fontFace: SERIF, fontSize: 11.5, italic: true, color: INK, align: "center", margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: dx + 0.15, y: sy, w: 1.1, h: 0.34, fill: { color: BG }, line: { color: INK, width: 1 } });
  s.addText("slot k", { x: dx + 0.15, y: sy, w: 1.1, h: 0.34, fontFace: CODE, fontSize: 11, color: INK, align: "center", valign: "middle", margin: 0 });
  // arrows A and B both to slot k
  s.addShape(pres.ShapeType.line, { x: bx + 1.3, y: cyA + 0.17, w: dx + 0.15 - (bx + 1.3), h: sy + 0.17 - (cyA + 0.17), line: { color: NAVY, width: 1.5, endArrowType: "triangle" } });
  s.addShape(pres.ShapeType.line, { x: bx + 1.3, y: cyB + 0.17, w: dx + 0.15 - (bx + 1.3), h: sy + 0.17 - (cyB + 0.17), line: { color: ALERT, width: 1.5, endArrowType: "triangle" } });
  s.addText("hash → ίδιο slot", { x: bx + 1.35, y: 3.68, w: dx - bx - 1.4, h: 0.3, fontFace: SERIF, fontSize: 11, italic: true, color: MUT, align: "center", margin: 0 });
  caption(s, bx, 5.02, dx + 1.4 - bx, "Σχήμα 4:", "A και B χτυπάνε το ίδιο slot → conflict miss.", "center");
  block(s, ML, 5.35, CW, 1.05, "Αυτό είναι το σημείο του Memstrata (§5.4)",
    "Line caching σε silicon δουλεύει — αλλά τα conflict misses χτυπάνε ακόμα χειρότερα όταν πολλές VMs μοιράζονται το cache. Θα το δούμε αναλυτικά.");
  s.addNotes("Το line caching δεν είναι δωρεάν: conflict misses, tag storage, 1:1 capacity. Γέφυρα προς Memstrata.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 11 — Pages or lines: the tradeoff
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(11, "§4.3", "4. Pages vs lines", "Pages ή lines; ο συμβιβασμός");
  caption(s, ML, 1.35, CW, "Πίνακας 3:", "page migration (software) vs line caching (hardware).");
  booktabs(s, ML, 1.68, [4.0, 3.8, 3.83], [
    [hb("Ιδιότητα"), hb("Page migration (OS)"), hb("Line caching (hardware)")],
    ["Unit", "4 KB / 2 MB", "64 B"],
    ["Ποιος αποφασίζει", "το OS, με παλιά πληροφορία", "το hardware, reactively"],
    ["Waste στο transfer", "Μεγάλο", "Σχεδόν μηδέν"],
    ["Σταθερό κόστος ανά κίνηση", { text: "μs (TLB shootdown)", options: { fontFace: CODE, fontSize: 12 } }, { text: "ns", options: { fontFace: CODE, fontSize: 12 } }],
    ["Metadata", "page tables (υπάρχουν ήδη)", "tag array — τεράστιο"],
    ["Capacity", "100% χρησιμοποιήσιμη", "το γρήγορο tier γίνεται cache"],
    ["Conflict misses", "Δεν υπάρχουν", "Ναι — και ανάμεσα σε VMs"],
    ["Νέο hardware", "Όχι", "Ναι"],
  ], [0.42, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4], { fs: 13 });
  s.addText(
    [
      { text: "Συμπέρασμα: ", options: { bold: true, color: ALERT } },
      { text: "κανένα από τα δύο δεν κερδίζει καθαρά. Τα papers παρακάτω διαλέγουν διαφορετικά σημεία πάνω σε αυτό το trade-off — γι' αυτό συνυπάρχουν.", options: {} },
    ],
    { x: ML, y: 5.7, w: CW, h: 0.9, fontFace: SERIF, fontSize: 14.5, color: INK, lineSpacing: 21, align: "justify", margin: 0 }
  );
  s.addNotes("Το ότι δεν υπάρχει καθαρός νικητής είναι ο λόγος που υπάρχουν 3 διαφορετικά papers.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 12 — Papers overview
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(12, "§5.1", "5. Τα papers", "Τα σχετικά papers: τρεις διαγνώσεις");
  caption(s, ML, 1.4, CW, "Πίνακας 4:", "και οι τρεις δείχνουν διαφορετική ρίζα για το ίδιο πρόβλημα.");
  booktabs(s, ML, 1.75, [1.95, 4.05, 3.9, 1.83], [
    [hb("Εργασία"), hb("Διάγνωση"), hb("Λύση"), hb("Granularity")],
    [{ text: "NeoMem\n(MICRO ’24)", options: { bold: true } }, "Το profiling είναι αργό/χοντρό — φτιάξ’ το και τα 4 KB pages φτάνουν", "Count-min sketch στον CXL controller + dynamic threshold", { text: "4 KB", options: { fontFace: CODE, fontSize: 12 } }],
    [{ text: "M5\n(ASPLOS ’25)", options: { bold: true, color: NAVY } }, { text: "Το hotness είναι sub-page — το access count ανά page σε ξεγελάει", options: { color: NAVY } }, { text: "Top-K trackers για pages (HPT) και για 64 B words (HWT)", options: { color: NAVY } }, { text: "profiling 64 B\nmigration 4 KB", options: { fontFace: CODE, fontSize: 10.5, bold: true, color: NAVY } }],
    [{ text: "Memstrata\n(OSDI ’24)", options: { bold: true } }, "Το hardware tiering δουλεύει — μέχρι να μπουν πολλές VMs και να συγκρουστούν", "Page coloring + online slowdown estimator", { text: "64 B (hardware)", options: { fontFace: CODE, fontSize: 11.5 } }],
  ], [0.42, 0.82, 0.82, 0.82]);
  s.addText(
    [
      { text: "Διαφωνούν, και αυτό βοηθάει: ", options: { bold: true } },
      { text: "NeoMem → λείπει resolution στον χρόνο. M5 → λείπει στον χώρο. Memstrata → το πρόβλημα βγαίνει μόνο με πολλά workloads μαζί. Μία διαφάνεια για το καθένα ακολουθεί.", options: {} },
    ],
    { x: ML, y: 5.5, w: CW, h: 1.0, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 22, align: "justify", margin: 0 }
  );
  s.addNotes("Overview. Οι επόμενες 3 διαφάνειες είναι το detail ανά paper.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 13 — M5 (detailed)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(13, "§5.2", "5. Τα papers", "M5 — sub-page hotness tracking (ASPLOS ’25)");
  itemize(s, ML, 1.45, 8.05, [
    ["Διάγνωση.", "Το hotness είναι sub-page. Το access count ανά page ξεγελάει: μια page με 500 accesses σε 2 words είναι κακός υποψήφιος· μια με 500 σε 40 words είναι καλός.", 0.85],
    ["Μηχανισμός.", "Δύο hardware trackers μέσα στη συσκευή CXL — HPT (top-K σε 4 KB pages) και HWT (top-K σε 64 B words). Δανεισμένοι από Rowhammer defenses (Misra–Gries counters).", 0.85],
    ["Το κλειδί.", "Profiling στα 64 B, migration στα 4 KB. Το word-level density λέει πόσο «πυκνά» hot είναι μια page — κάτι που το σκέτο count δεν ξέρει.", 0.75],
  ], 14);
  block(s, 9.15, 1.45, CW - (9.15 - ML), 2.55, "Αποτελέσματα",
    "• +47% πιο hot pages απ' τα baselines\n\n• +20% vs AutoNUMA\n\n• +14% vs DAMON");
  block(s, ML, 4.7, CW, 1.5, "Γιατί το διαλέγω",
    "Είναι το πιο κοντινό στην ιδέα του sub-page hotness. Το hardware είναι απλό (counter tables), και " +
    "το split profiling → decision υλοποιείται καθαρά μέσα στον CXLRAMSim. Θα φτιάξω πρώτα το HPT, μετά " +
    "το HWT σαν το κομμάτι που κάνει τη διαφορά.", false);
  s.addNotes("Το επιλεγμένο paper. HPT+HWT, top-K counters. Profiling 64B, migration 4KB.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 14 — NeoMem (detailed)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(14, "§5.3", "5. Τα papers", "NeoMem — profiling στον CXL controller (MICRO ’24)");
  itemize(s, ML, 1.45, 8.05, [
    ["Διάγνωση.", "Το profiling είναι αργό/χοντρό. Φτιάξ' το και τα 4 KB pages φτάνουν — το granularity είναι δευτερεύον.", 0.72],
    ["Μηχανισμός (NeoProf).", "Count-min sketch μέσα στον controller: W×D counters, D hashes, min ως estimate. Hot-page filtering με bloom bits. Histogram για error bounds. Μετράει και bandwidth + ping-pong.", 0.98],
    ["Policy.", "Dynamic threshold = p-percentile, προσαρμόζεται με bandwidth & ping-pong. Migration quota 256 MB/s. Τα cold pages: reuse του Linux LRU.", 0.75],
  ], 14);
  block(s, 9.15, 1.45, CW - (9.15 - ML), 2.75, "Αποτελέσματα",
    "• 32–67% geomean speedup\n\n• 4.7× GUPS · 3.5× XSBench\n\n• 1.58× vs Memtis\n\n• HW: 5.3 mm², 152 mW\n  0.02% CPU overhead");
  block(s, ML, 4.65, CW, 1.55, "Σχέση με εμένα",
    "Το sketch είναι εύκολο να υλοποιηθεί (λίγες γραμμές, όλα τα params δίνονται). Αλλά το βάρος της " +
    "συνεισφοράς πέφτει στο kernel daemon και το policy — πιο software απ' όσο θέλω, αφού εστιάζω στο " +
    "hardware. Καλή δεύτερη επιλογή· το threshold-adaptation του αξίζει να το δανειστώ.", false);
  s.addNotes("Δεύτερη επιλογή. Sketch εύκολο, αλλά το ενδιαφέρον είναι στο kernel daemon.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 15 — Memstrata (detailed)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(15, "§5.4", "5. Τα papers", "Memstrata — hardware tiering + multi-tenant (OSDI ’24)");
  itemize(s, ML, 1.45, 8.05, [
    ["Context: Flat Memory Mode.", "Intel: η τοπική DRAM γίνεται direct-mapped, line-granular (64 B), 1:1 cache μπροστά από την CXL. Transparent στο OS.", 0.78],
    ["Το πρόβλημα.", "Καλό κατά μέσο όρο, κακό στο tail. Πολλές VMs → τα lines τους πέφτουν στο ίδιο slot και η μία ρίχνει την άλλη αόρατα (>30%).", 0.82],
    ["Λύση.", "Ελαφρύς allocator: page coloring ώστε οι VMs να μη συγκρούονται + online slowdown estimator που δίνει παραπάνω τοπική DRAM στις ευαίσθητες.", 0.82],
  ], 14);
  block(s, 9.15, 1.45, CW - (9.15 - ML), 2.6, "Αποτελέσματα",
    "• ≤5% degradation σε\n  >82% των workloads\n\n• Outliers: 30% → <6%\n\n• Καθαρά software πάνω\n  σε hardware tiering");
  block(s, ML, 4.75, CW, 1.45, "Σχέση με εμένα",
    "Το αντιπαράδειγμα: line granularity σε silicon. Δείχνει τι κοστίζει στην πράξη — conflict misses, " +
    "multi-tenant interference, 1:1 capacity. Δεν το υλοποιώ: ο CXLRAMSim δεν μοντελοποιεί Flat Memory " +
    "Mode, οπότε θα έπρεπε πρώτα να χτίσω το hardware tiering και μετά τον allocator.", false);
  s.addNotes("Το αντιπαράδειγμα. Line granularity σε silicon, και τι κοστίζει. Δεν το υλοποιώ.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 16 — The tool
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(16, "§6.1", "6. Μεθοδολογία", "Το εργαλείο: CXLRAMSim");
  s.addText(
    "Full-system προσομοιωτής πάνω στο gem5 v25, που μπουτάρει Linux 6.14. Βάζει τη συσκευή CXL στη σωστή " +
    "θέση πάνω στο I/O bus, οπότε ο kernel, οι drivers και το software stack μένουν αναλλοίωτα.",
    { x: ML, y: 1.45, w: CW, h: 0.7, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );
  s.addText("Τι μοντελοποιεί:", { x: ML, y: 2.35, w: CW, h: 0.32, fontFace: SERIF, fontSize: 14.5, bold: true, color: INK, margin: 0 });
  const comps = [["Firmware.", "ACPI tables (MCFG, DSDT, CEDT, SRAT) για το discovery."], ["CXL.io.", "Root Complex και registers για το enumeration."], ["CXL.mem.", "transaction layer, M2S / S2M channels, packetization."], ["Coherence.", "MESI δύο επιπέδων με directory (Ruby)."]];
  comps.forEach(([h, d], i) => {
    const y = 2.72 + i * 0.4;
    s.addText("–", { x: ML + 0.1, y, w: 0.3, h: 0.32, fontFace: SERIF, fontSize: 14.5, color: NAVY, margin: 0 });
    s.addText([{ text: h + " ", options: { bold: true, fontFace: CODE, fontSize: 12.5 } }, { text: d, options: {} }], { x: ML + 0.45, y, w: CW - 0.45, h: 0.34, fontFace: SERIF, fontSize: 14, color: INK, valign: "middle", margin: 0 });
  });
  block(s, ML, 4.55, CW, 1.9, "Πού μπαίνει ο δικός μου κώδικας",
    "Εκεί που ο CXL node κάνει de-packetize ένα M2S request σε access στη DRAM, έχω το triple " +
    "{physical address, read/write, timestamp}. Αυτό είναι ακριβώς το stream των LLC misses προς την " +
    "CXL που κάνουν profiling το NeoMem και το M5· τίποτα άλλο δεν φαίνεται από εκεί.\n\nΟ HPT/HWT " +
    "profiler μπαίνει σαν tap πάνω σε αυτό το path.");
  s.addNotes("Ανοιχτό θέμα: χρειάζομαι το repo του CXLRAMSim — δεν βρήκα δημόσιο.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 17 — Experiment plan
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(17, "§6.2", "6. Μεθοδολογία", "Σχέδιο του πειράματος");
  s.addText("Πέντε cases για σύγκριση.", { x: ML, y: 1.42, w: 5.6, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  [["Όλα στην CXL", "lower bound"], ["Όλα σε τοπική DRAM", "upper bound"], ["Απλό page migration", "το «πρόβλημα»"], ["Ο μηχανισμός του M5 (HPT+HWT)", "η πρόταση"], ["Oracle placement", "offline βέλτιστο"]].forEach(([a, tag], i) => {
    const y = 1.82 + i * 0.44;
    s.addText(`${i + 1}.`, { x: ML, y, w: 0.35, h: 0.3, fontFace: SERIF, fontSize: 14, color: NAVY, margin: 0 });
    s.addText([{ text: a, options: { bold: i === 2 || i === 3 } }, { text: "  — " + tag, options: { italic: true, color: MUT } }], { x: ML + 0.4, y, w: 5.5, h: 0.34, fontFace: SERIF, fontSize: 14, color: INK, valign: "middle", margin: 0 });
  });
  s.addText("Η απόσταση απλό migration ↔ oracle είναι το πρόβλημα που θέλω να δείξω.", { x: ML, y: 4.1, w: 5.7, h: 0.7, fontFace: SERIF, fontSize: 14, italic: true, color: ALERT, lineSpacing: 20, margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: 6.75, y: 1.45, w: 0.01, h: 4.4, fill: { color: RULE } });
  s.addText("Workloads.", { x: 7.1, y: 1.42, w: 5.4, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  s.addText(
    [
      { text: "GUPS", options: { fontFace: CODE, fontSize: 12 } }, { text: " — τυχαία 8 B updates, μηδέν locality (worst case)\n", options: {} },
      { text: "XSBench", options: { fontFace: CODE, fontSize: 12 } }, { text: " — Monte Carlo lookups σε μεγάλα tables\n", options: {} },
      { text: "PageRank", options: { fontFace: CODE, fontSize: 12 } }, { text: " — irregular graph, το hot set μετακινείται\n", options: {} },
      { text: "Btree / YCSB-C", options: { fontFace: CODE, fontSize: 12 } }, { text: " — Zipf, ακραίο sub-page hotness", options: {} },
    ],
    { x: 7.1, y: 1.8, w: 5.4, h: 1.6, fontFace: SERIF, fontSize: 13.5, color: INK, lineSpacing: 20, margin: 0 }
  );
  s.addText("Metrics.", { x: 7.1, y: 3.8, w: 5.4, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  s.addText(
    [
      { text: "– CDF του access density ανά 64 B line\n", options: {} },
      { text: "– migration efficiency: useful ÷ moved bytes\n", options: {} },
      { text: "– promotion timeliness (πόσα ακόμα hot)\n", options: {} },
      { text: "– slowdown vs fast-tier ratio · ping-pongs", options: {} },
    ],
    { x: 7.1, y: 4.18, w: 5.4, h: 1.7, fontFace: SERIF, fontSize: 13, color: INK, lineSpacing: 19, margin: 0 }
  );
  s.addNotes("Πάντα αναφέρω και τα δύο bounds δίπλα σε κάθε case.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 18 — The figure
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(18, "§6.3", "6. Μεθοδολογία", "Το σχήμα που θα το κρίνει");
  s.addText(
    "Για κάθε page 4 KB: τι ποσοστό των accesses του πέφτει στις k πιο hot 64 B lines. Αν το 80% πέφτει " +
    "σε <10% του page, το επιχείρημα του granularity αποδεικνύεται με ένα γράφημα.",
    { x: ML, y: 1.45, w: 5.15, h: 1.5, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 23, align: "justify", margin: 0 }
  );
  s.addText(
    [{ text: "Επιφύλαξη. ", options: { bold: true, color: ALERT } }, { text: "Η καμπύλη είναι το αναμενόμενο σχήμα, όχι δεδομένα· ο προσομοιωτής δεν έχει τρέξει ακόμα. Αν βγει επίπεδη, το επιχείρημα του sub-page hotness πέφτει για αυτό το workload — εξίσου χρήσιμο.", options: {} }],
    { x: ML, y: 3.2, w: 5.15, h: 1.9, fontFace: SERIF, fontSize: 14, color: INK, lineSpacing: 21, align: "justify", margin: 0 }
  );
  const cats = ["1", "4", "8", "16", "24", "32", "48", "64"];
  s.addChart(pres.ChartType.line, [
    { name: "Zipf (Btree / YCSB)", labels: cats, values: [31, 62, 78, 88, 93, 96, 99, 100] },
    { name: "Uniform (GUPS)", labels: cats, values: [2, 6, 13, 25, 38, 50, 75, 100] },
  ], {
    x: 6.35, y: 1.5, w: 6.13, h: 4.05, showTitle: false,
    chartColors: [NAVY, ALERT], lineSize: 2.25, lineSmooth: true, lineDash: ["solid", "dash"],
    showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: INK, legendFontFace: SERIF,
    catAxisTitle: "k πιο hot 64 B lines (από 64)", showCatAxisTitle: true, catAxisTitleFontSize: 11, catAxisTitleColor: MUT, catAxisTitleFontFace: SERIF,
    valAxisTitle: "cumulative %", showValAxisTitle: true, valAxisTitleFontSize: 11, valAxisTitleColor: MUT, valAxisTitleFontFace: SERIF,
    catAxisLabelColor: INK, valAxisLabelColor: INK, catAxisLabelFontFace: SERIF, valAxisLabelFontFace: SERIF,
    catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
    valAxisMaxVal: 100, valAxisMinVal: 0, valAxisMajorUnit: 25,
    valGridLine: { color: "E3E3E3", size: 1 }, catGridLine: { style: "none" },
  });
  caption(s, 6.35, 5.65, 6.13, "Σχήμα 7:", "cumulative % των accesses στις k πιο hot 64 B lines (αναμενόμενο σχήμα).", "center");
  s.addNotes("Σκίτσο, όχι δεδομένα — το δηλώνω. Ο Zipf δείχνει συγκέντρωση· το GUPS είναι negative control.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 19 — Roadmap
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(19, "§6.4", "6. Μεθοδολογία", "Φάσεις υλοποίησης και ρίσκο");
  const phases = [
    ["Φάση 1.", "Boot & checkpoint.", "Boot μέχρι shell, zNUMA node, latency microbenchmark («η CXL είναι όντως πιο αργή»)."],
    ["Φάση 2.", "Access tracing.", "Tap στο request stream + CDF του access density — το πρώτο πραγματικό αποτέλεσμα."],
    ["Φάση 3.", "Baseline migration.", "Απλό page migration με τίμιο cost model και bandwidth quota."],
    ["Φάση 4.", "Υλοποίηση του M5.", "Πρώτα ο HPT (hot pages), μετά ο HWT (hot 64 B words)."],
    ["Φάση 5.", "Evaluation & γράψιμο.", "Sensitivity ως προς K, interval, quota, CXL latency."],
  ];
  phases.forEach(([p, h, d], i) => {
    const y = 1.5 + i * 0.82;
    const hot = i === 1;
    s.addText(p, { x: ML, y, w: 1.15, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: hot ? ALERT : NAVY, margin: 0, valign: "top" });
    s.addText([{ text: h + " ", options: { bold: true, color: hot ? ALERT : INK } }, { text: d, options: {} }], { x: ML + 1.2, y, w: CW - 1.2, h: 0.7, fontFace: SERIF, fontSize: 14.5, color: INK, lineSpacing: 20, align: "justify", margin: 0, valign: "top" });
    if (i < 4) s.addShape(pres.ShapeType.rect, { x: ML + 1.2, y: y + 0.7, w: CW - 1.2, h: 0.006, fill: { color: "E8E8E8" } });
  });
  s.addText("Η Φάση 2 μειώνει το ρίσκο όλων των υπολοίπων: βγάζει παρουσιάσιμο αποτέλεσμα πριν γραφτεί οποιοδήποτε policy.",
    { x: ML, y: 5.75, w: CW, h: 0.6, fontFace: SERIF, fontSize: 14, italic: true, color: MUT, lineSpacing: 21, margin: 0 });
  s.addNotes("Core vs stretch. Η Φάση 2 είναι το de-risking.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 20 — Open questions
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(20, "§7", "7. Συζήτηση", "Ανοιχτά ερωτήματα για συζήτηση");
  const qs = [
    ["Πρόσβαση στον CXLRAMSim.", "Υπάρχει repo και οδηγίες build; Ιδανικά και έτοιμο disk image — το χτίσιμο από το μηδέν είναι μέρες δουλειάς που δεν διδάσκουν κάτι για το tiering."],
    ["Μέγεθος των workloads.", "Είναι ok να κατεβάσω το μέγεθος σε εκατοντάδες MB αντί για 10–20 GB RSS, κρατώντας ρεαλιστικό το ratio των tiers;"],
    ["Πόσο μακριά να πάει το implementation.", "Φτάνει profiler HPT+HWT με μοντελοποιημένο migration engine, ή θέλετε πραγματικό Linux migration από kernel module;"],
    ["Επιλογή paper.", "Είναι το M5 η σωστή επιλογή, ή προτιμάτε να δείτε NeoMem;"],
  ];
  qs.forEach(([h, d], i) => {
    const y = 1.55 + i * 1.05;
    s.addText(`${i + 1}.`, { x: ML, y, w: 0.45, h: 0.32, fontFace: SERIF, fontSize: 16, bold: true, color: NAVY, margin: 0 });
    s.addText(h, { x: ML + 0.5, y, w: CW - 0.5, h: 0.34, fontFace: SERIF, fontSize: 16, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: ML + 0.5, y: y + 0.36, w: CW - 0.5, h: 0.6, fontFace: SERIF, fontSize: 14, color: INK, lineSpacing: 20, align: "justify", margin: 0 });
  });
  s.addNotes("Έτοιμη απάντηση για «γιατί όχι κατευθείαν cache lines»: δεν υπάρχει PTE για line → hardware indirection → Flat Memory Mode → conflict misses/capacity → αυτό λύνει το Memstrata.");
}

const out = path.join(__dirname, "..", "docs", "memory-tiering-cxl-gr.pptx");
pres.writeFile({ fileName: out }).then(() => console.log("wrote " + out + " (" + TOTAL + " slides)"));
