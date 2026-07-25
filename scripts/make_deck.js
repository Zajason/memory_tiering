// Generates docs/memory-tiering-cxl-gr.pptx — concept presentation (Greek)
// Content follows docs/presentation-outline.md
//
// Visual paradigm: an academic conference talk (LaTeX/Beamer). Serif type
// throughout (Times New Roman), white background, numbered sections (§3.2) and
// captioned figures/tables (Σχήμα N, Πίνακας N) in booktabs style, dense prose,
// a thin footline, and only two restrained colors used the way Beamer uses
// \structure{} (navy) and \alert{} (dark red).
//
// Language note: technical terms stay in English (Latin script), the way Greek
// CS/ECE students actually write and speak — tiering, granularity, bandwidth,
// latency, page migration, profiling, promotion/demotion, hot pages, etc.
//
// Run: node scripts/make_deck.js

const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33" x 7.5"
pres.author = "el23408";
pres.title = "Memory Tiering σε συστήματα CXL";

// ── Palette (paper) ──────────────────────────────────────────────────────────
const BG = "FFFFFF";
const INK = "1A1A1A";
const MUT = "6E6E6E";
const NAVY = "1F3A63"; // \structure — section numbers, headings
const ALERT = "8C2A2A"; // \alert — sparing emphasis
const RULE = "BFBFBF"; // hairlines
const BLK = "F0F0EE"; // block body fill
const BLKA = "F7ECEC"; // alert-block body fill

const SERIF = "Times New Roman";
const CODE = "Courier New";

const ML = 0.85;
const MR = 12.48;
const CW = MR - ML; // 11.63
const FOOT = "Memory Tiering σε συστήματα CXL  ·  el23408";

// ── Helpers ──────────────────────────────────────────────────────────────────
function frame(n, sec, secName, ttl) {
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText(
    [
      { text: `${sec}  `, options: { color: NAVY, bold: true } },
      { text: ttl, options: { color: INK, bold: true } },
    ],
    { x: ML, y: 0.42, w: CW, h: 0.55, fontFace: SERIF, fontSize: 24, margin: 0, valign: "middle" }
  );
  s.addShape(pres.ShapeType.rect, { x: ML, y: 7.04, w: CW, h: 0.008, fill: { color: RULE } });
  s.addText(FOOT, { x: ML, y: 7.1, w: 6.5, h: 0.3, fontFace: SERIF, fontSize: 9.5, color: MUT, margin: 0, valign: "middle" });
  s.addText(secName, { x: ML + 6.5, y: 7.1, w: 3.5, h: 0.3, fontFace: SERIF, fontSize: 9.5, italic: true, color: MUT, align: "center", margin: 0, valign: "middle" });
  s.addText(`${n} / 14`, { x: MR - 1.5, y: 7.1, w: 1.5, h: 0.3, fontFace: SERIF, fontSize: 9.5, color: MUT, align: "right", margin: 0, valign: "middle" });
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
    [
      { text: label + " ", options: { bold: true } },
      { text: text, options: {} },
    ],
    { x, y, w, h: 0.32, fontFace: SERIF, fontSize: 11, italic: true, color: MUT, align, margin: 0 }
  );
}

function block(s, x, y, w, h, title, body, alert) {
  s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color: alert ? BLKA : BLK } });
  s.addText(title, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.32, fontFace: SERIF, fontSize: 14.5, bold: true, color: alert ? ALERT : NAVY, margin: 0 });
  s.addText(body, { x: x + 0.2, y: y + 0.48, w: w - 0.4, h: h - 0.6, fontFace: SERIF, fontSize: 13.5, color: INK, lineSpacing: 19, margin: 0, valign: "top" });
}

// ═════════════════════════════════════════════════════════════════════════════
// 01 — Title page
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG };

  s.addText("Προηγμένη Αρχιτεκτονική Υπολογιστών  ·  Εργασία 2  ·  Παρουσίαση ιδέας", {
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
    [
      { text: "Keywords:  ", options: { bold: true } },
      { text: "CXL · memory tiering · page migration · hardware profiling · granularity", options: { italic: true } },
    ],
    { x: ML + 0.35, y: 5.15, w: CW - 0.35, h: 0.32, fontFace: SERIF, fontSize: 13, color: MUT, margin: 0 }
  );

  s.addShape(pres.ShapeType.rect, { x: ML, y: 5.75, w: CW, h: 0.014, fill: { color: RULE } });
  s.addText(
    [
      { text: "el23408", options: { bold: true } },
      { text: "   ·   Εθνικό Μετσόβιο Πολυτεχνείο   ·   Ιούλιος 2026", options: {} },
    ],
    { x: ML, y: 5.95, w: CW, h: 0.35, fontFace: SERIF, fontSize: 14, color: INK, margin: 0 }
  );
  s.addText("github.com/Zajason/memory_tiering", {
    x: ML, y: 6.35, w: CW, h: 0.3, fontFace: CODE, fontSize: 11, color: MUT, margin: 0,
  });

  s.addNotes("Στόχος: δείχνω ότι κατάλαβα το πρόβλημα και ότι έχω αξιόπιστο πλάνο. Δεν έχω ακόμα αποτελέσματα, και το λέω ανοιχτά.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 02 — Motivation
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(2, "§1.1", "1. Κίνητρο", "Η μνήμη είναι το bottleneck");

  s.addText(
    "Η capacity της μνήμης ανά socket έχει κολλήσει: λίγα DIMM slots, λίγα pins στο DDR. Για να βάλεις " +
    "παραπάνω μνήμη πρέπει να πάρεις κι άλλους επεξεργαστές που δεν σου χρειάζονται. Το CXL σπάει αυτή " +
    "τη σχέση: βάζεις μνήμη πάνω από το PCIe, ανεξάρτητα από τα cores.",
    { x: ML, y: 1.45, w: CW, h: 1.35, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );

  block(
    s, ML, 3.0, CW, 1.35, "Το νούμερο — stranded μνήμη",
    "Σε μεγάλα cloud datacenters, περίπου το 25% της DRAM μένει αχρησιμοποίητο (stranded), γιατί τα " +
    "cores του μηχανήματος έχουν ήδη νοικιαστεί σε άλλους. Το CXL στοχεύει ακριβώς σε αυτή τη χαμένη " +
    "capacity (Azure — Pond, ASPLOS ’23)."
  );

  s.addText(
    "Το κίνητρο είναι η φθηνή, κοινή capacity. Το κόστος είναι το latency, που το βλέπουμε στην επόμενη διαφάνεια.",
    { x: ML, y: 4.65, w: CW, h: 0.7, fontFace: SERIF, fontSize: 15, italic: true, color: MUT, lineSpacing: 22, align: "justify", margin: 0 }
  );

  s.addNotes("Ένα νούμερο να μείνει: ~25% stranded DRAM. Το οικονομικό κίνητρο όλου του πεδίου.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 03 — What CXL costs
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(3, "§1.2", "1. Κίνητρο", "Το κόστος: το latency της CXL");

  caption(s, ML, 1.4, 6.7, "Πίνακας 1:", "τυπικές τιμές latency και bandwidth ανά διαδρομή.");
  booktabs(s, ML, 1.75, [2.9, 2.0, 1.8], [
    [hb("Διαδρομή"), hb("Latency"), hb("Bandwidth")],
    ["Τοπική DDR5", { text: "80–100 ns", options: { fontFace: CODE, fontSize: 12 } }, "30–50 GB/s"],
    ["Άλλο NUMA socket", { text: "140–180 ns", options: { fontFace: CODE, fontSize: 12 } }, "—"],
    [
      { text: "CXL (x8 Gen5)", options: { bold: true } },
      { text: "250–400 ns", options: { fontFace: CODE, fontSize: 12, bold: true, color: ALERT } },
      { text: "25–30 GB/s", options: { bold: true } },
    ],
  ], [0.42, 0.42, 0.42, 0.42]);

  s.addText(
    [
      { text: "Το latency είναι ", options: {} },
      { text: "2–3× μεγαλύτερο", options: { bold: true, color: ALERT } },
      { text: " από την τοπική DDR, παρόλο που η DRAM πάνω στην κάρτα είναι κοινή DDR5. Το κόστος το βάζει το interconnect, όχι η μνήμη. Οπότε workloads που είναι latency-bound (pointer chasing) υποφέρουν, ενώ τα bandwidth-bound σχεδόν δεν το καταλαβαίνουν.", options: {} },
    ],
    { x: ML, y: 3.9, w: 6.7, h: 1.7, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 23, align: "justify", margin: 0 }
  );

  const fx = 8.15, fw = CW - (fx - ML);
  s.addText("Διαδρομή ενός load με LLC miss:", {
    x: fx, y: 1.4, w: fw, h: 0.32, fontFace: SERIF, fontSize: 13.5, italic: true, color: INK, margin: 0,
  });
  const steps = [
    "Core  →  LLC miss", "CXL Root Complex", "packetization (M2S)", "PCIe link (SERDES)",
    "device controller  →  de-packetize", "DRAM στην κάρτα", "και όλη η διαδρομή πίσω (S2M)",
  ];
  steps.forEach((t, i) => {
    const y = 1.85 + i * 0.42;
    s.addText(`(${i + 1})`, { x: fx, y, w: 0.5, h: 0.32, fontFace: CODE, fontSize: 12, color: NAVY, margin: 0, valign: "middle" });
    s.addText(t, { x: fx + 0.55, y, w: fw - 0.55, h: 0.32, fontFace: SERIF, fontSize: 14, color: i === 6 ? MUT : INK, italic: i === 6, margin: 0, valign: "middle" });
  });
  caption(s, fx, 4.98, fw, "Σχήμα 1:", "κάθε στάδιο προσθέτει latency· κυριαρχεί το interconnect.");

  s.addNotes("Το σημείο: η DRAM στην κάρτα είναι κανονική DDR5. Το interconnect είναι ο φόρος — γι' αυτό υπάρχει tiering.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 04 — The tiering problem stated
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(4, "§2", "2. Το πρόβλημα", "Το πρόβλημα του tiering");

  s.addText(
    "Έχουμε δύο tiers μνήμης: ένα γρήγορο και μικρό (τοπική DDR) κι ένα αργό και μεγάλο (CXL). Θέλουμε " +
    "τα hot data να μένουν στο γρήγορο tier. Αν το πετύχεις, ένα μηχάνημα με 25% τοπική DRAM τρέχει " +
    "σχεδόν σαν να είχε 100%.",
    { x: ML, y: 1.45, w: CW, h: 0.95, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );

  const bw = (CW - 0.4) / 2;
  block(s, ML, 2.55, bw, 1.55, "Promotion",
    "Μετακίνηση ενός page από το αργό στο γρήγορο tier. Πρέπει να γίνει στην ώρα του: αν ένα page " +
    "προαχθεί αφού έχει κρυώσει, είναι χαμένος κόπος.");
  block(s, ML + bw + 0.4, 2.55, bw, 1.55, "Demotion",
    "Μετακίνηση ενός page από το γρήγορο στο αργό tier. Πρέπει να είναι ασφαλής: αν κατεβάσεις ένα page " +
    "που είναι ακόμα hot, ξεκινάει ping-pong.");

  s.addText(
    [
      { text: "Το demotion είναι το εύκολο κομμάτι: ένα LRU αρκεί, και το Linux ήδη έχει LRU. ", options: {} },
      { text: "Το promotion είναι το δύσκολο.", options: { bold: true, color: ALERT } },
      { text: " Πρέπει να ξέρεις ότι ένα page είναι hot τώρα, κι αυτό κοστίζει. Το λέει και η ίδια η κοινότητα του Linux MM.", options: {} },
    ],
    { x: ML, y: 4.4, w: CW, h: 1.4, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );

  s.addNotes("Γιατί δύσκολο το promotion: πρέπει να ξέρεις ότι ένα page είναι hot ΤΩΡΑ.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 05 — Failure mode 1: profiling
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(5, "§3.1", "3. Γιατί δεν δουλεύει", "Γιατί δεν δουλεύει: το profiling");

  caption(s, ML, 1.4, CW, "Πίνακας 2:", "τρόποι εντοπισμού των hot pages και το βασικό πρόβλημα του καθενός.");
  booktabs(s, ML, 1.75, [2.6, 4.0, 5.03], [
    [hb("Μηχανισμός"), hb("Πώς δουλεύει"), hb("Βασικό πρόβλημα")],
    [
      { text: "PTE-scan (DAMON)", options: { fontFace: CODE, fontSize: 11.5 } },
      "Σαρώνει τα access bits των PTE",
      "1 bit = ναι/όχι. Το scan κρατάει δευτερόλεπτα, οπότε το hot set έχει ήδη αλλάξει",
    ],
    [
      { text: "hint faults (AutoNUMA, TPP)", options: { fontFace: CODE, fontSize: 11 } },
      "Κάνει unmap τα PTE ώστε το επόμενο access να πέσει σε fault",
      { text: "Μετράει TLB misses, όχι LLC misses — δεν συσχετίζονται καλά", options: { color: ALERT } },
    ],
    [
      { text: "PEBS / IBS (Memtis)", options: { fontFace: CODE, fontSize: 11.5 } },
      "Sampling του PMU πάνω σε LLC misses",
      "Το overhead ανεβαίνει με το sampling rate: >50% slowdown σε πυκνό sampling",
    ],
    [
      { text: "hardware μέσα στην CXL", options: { fontFace: CODE, fontSize: 11.5, color: NAVY, bold: true } },
      { text: "Counters μέσα στον controller της συσκευής", options: { color: NAVY } },
      { text: "Σωστό event, μηδέν κόστος CPU — αλλά θέλει καινούριο hardware", options: { color: NAVY, bold: true } },
    ],
  ], [0.42, 0.7, 0.7, 0.7, 0.62]);

  s.addText(
    [
      { text: "Το σημαντικό. ", options: { bold: true, color: ALERT } },
      { text: "AutoNUMA και TPP μετράνε TLB misses, αλλά το traffic προς την CXL το καθορίζουν τα LLC misses. Ένα page μπορεί να είναι πολύ hot στο TLB και σχεδόν αόρατο στην CXL. Δηλαδή βελτιστοποιούν το λάθος σήμα.", options: {} },
    ],
    { x: ML, y: 5.55, w: CW, h: 1.1, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 22, align: "justify", margin: 0 }
  );

  s.addNotes("Κοινός παρονομαστής: accuracy × timeliness × overhead — διάλεξε δύο.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 06 — Failure mode 2: granularity (central)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(6, "§3.2", "3. Γιατί δεν δουλεύει", "Γιατί δεν δουλεύει: το granularity");

  s.addText(
    "Μέσα σε ένα page 4 KB, τα accesses δεν είναι μοιρασμένα ομοιόμορφα. Ένα lookup σε hash table αγγίζει " +
    "64 bytes από τα 4096 (Σχήμα 2). Το 4 KB είναι λάθος unit και προς τις δύο μεριές: πολύ μεγάλο για το " +
    "τι είναι πραγματικά hot, αλλά και πολύ μικρό για τον μηχανισμό του migration, που πληρώνει σταθερό " +
    "κόστος ανά page.",
    { x: ML, y: 1.42, w: CW, h: 1.35, fontFace: SERIF, fontSize: 15.5, color: INK, lineSpacing: 23, align: "justify", margin: 0 }
  );

  const cols = [["64 B", "cache line", "ελάχιστο waste· τα metadata εκτοξεύονται"],
                ["4 KB", "default του Linux", "μέτριο και στα δύο: κάνει waste και κοστίζει"],
                ["2 MB", "huge page", "φθηνό migration· τεράστιο waste (>99%)"]];
  const cwv = (CW - 1.0) / 3;
  cols.forEach((c, i) => {
    const x = ML + i * (cwv + 0.5);
    s.addText(c[0], { x, y: 2.95, w: cwv, h: 0.5, fontFace: SERIF, fontSize: 28, bold: true, color: NAVY, align: "center", margin: 0 });
    s.addText(c[1], { x, y: 3.5, w: cwv, h: 0.28, fontFace: CODE, fontSize: 11, color: MUT, align: "center", margin: 0 });
    s.addText(c[2], { x, y: 3.82, w: cwv, h: 0.6, fontFace: SERIF, fontSize: 12.5, italic: true, color: INK, align: "center", lineSpacing: 16, margin: 0 });
    if (i < 2) s.addText("−→", { x: x + cwv, y: 2.95, w: 0.5, h: 0.5, fontFace: SERIF, fontSize: 20, color: MUT, align: "center", valign: "middle", margin: 0 });
  });
  caption(s, ML, 4.5, CW, "Σχήμα 2:", "το φάσμα του granularity — καμία επιλογή δεν είναι καλή και στα δύο ταυτόχρονα.", "center");

  block(s, ML, 5.0, CW, 1.55,
    "Το ουσιαστικό — δεν υπάρχει PTE για cache line",
    "Άρα δεν γίνεται να κάνεις migrate cache lines αντί για pages μέσα από το OS. Ή βάζεις hardware " +
    "indirection (η τοπική DRAM γίνεται cache γραμμών), ή —κι εδώ στοχεύω— κάνεις profiling σε λεπτό " +
    "granularity (64 B) και migration σε χοντρό (4 KB). Το granularity του profiling δεν είναι ίδιο με " +
    "του migration· αυτό ακριβώς κάνει το M5.",
    true
  );

  s.addNotes("Εδώ θα με ρωτήσουν. Απάντηση: profiling granularity ≠ migration granularity. Το M5 profiling στα 64 B, migration στα 4 KB.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 07 — Failure mode 3: migration cost
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(7, "§3.3", "3. Γιατί δεν δουλεύει", "Γιατί δεν δουλεύει: το κόστος του migration");

  s.addText("Για να προαχθεί ένα page 4 KB, το OS πληρώνει τέσσερα κόστη:", {
    x: ML, y: 1.42, w: CW, h: 0.35, fontFace: SERIF, fontSize: 16, color: INK, margin: 0,
  });

  const costs = [
    ["Copy.", "4 KB read από CXL + 4 KB write σε DDR — τρώει το bandwidth που θέλεις να γλιτώσεις."],
    ["Ενημέρωση page table.", "Διάσχιση του rmap για κάθε PTE που δείχνει στο page."],
    ["TLB shootdown.", "IPI σε κάθε core με πιθανό cached translation — συνήθως το πιο ακριβό."],
    ["Lock contention.", "mmap_lock, LRU locks· δεν κάνει καλό scaling."],
  ];
  costs.forEach(([h, d], i) => {
    const y = 1.95 + i * 0.8;
    const hot = i === 2;
    s.addText(`${i + 1}.`, { x: ML, y, w: 0.4, h: 0.6, fontFace: SERIF, fontSize: 14.5, bold: true, color: hot ? ALERT : NAVY, margin: 0, valign: "top" });
    s.addText(
      [
        { text: h + " ", options: { bold: true, color: hot ? ALERT : INK } },
        { text: d, options: {} },
      ],
      { x: ML + 0.45, y, w: 6.5, h: 0.7, fontFace: SERIF, fontSize: 13.5, color: INK, lineSpacing: 19, align: "justify", margin: 0, valign: "top" }
    );
  });

  block(s, 8.05, 1.95, CW - (8.05 - ML), 3.15, "Τάξη μεγέθους",
    "Ένα migration ενός page κοστίζει μsec — χιλιάδες φορές πάνω από τα ~250 ns που προσπαθείς να " +
    "αποφύγεις ανά access.\n\n" +
    "Άρα ένα page πρέπει να ξαναχρησιμοποιηθεί πολλές φορές για να αξίζει το migration. Γι’ αυτό ένα " +
    "λάθος promotion δεν είναι απλώς άχρηστο· είναι και επιζήμιο.");

  s.addText(
    "Αυτό το κόστος είναι που επιβάλλει quota στο migration bandwidth και hysteresis στις αποφάσεις, ώστε " +
    "ο μηχανισμός να μην καίει τους πόρους που υποτίθεται ότι γλιτώνει.",
    { x: ML, y: 5.35, w: CW, h: 0.85, fontFace: SERIF, fontSize: 14.5, italic: true, color: MUT, lineSpacing: 21, align: "justify", margin: 0 }
  );

  s.addNotes("Τάξη μεγέθους: μsec έναντι ns. Χιλιαπλάσιο κόστος.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 08 — Three papers
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(8, "§4.1", "4. Σχετικές εργασίες", "Τρεις εργασίες, τρεις διαφορετικές διαγνώσεις");

  caption(s, ML, 1.4, CW, "Πίνακας 3:", "και οι τρεις δείχνουν διαφορετική ρίζα για το ίδιο πρόβλημα.");
  booktabs(s, ML, 1.75, [1.95, 4.05, 3.9, 1.83], [
    [hb("Εργασία"), hb("Διάγνωση"), hb("Λύση"), hb("Granularity")],
    [
      { text: "NeoMem\n(MICRO ’24)", options: { bold: true } },
      "Το profiling είναι αργό και χοντρό — φτιάξ’ το και τα 4 KB pages φτάνουν",
      "Count-min sketch μέσα στον CXL controller + dynamic hotness threshold",
      { text: "4 KB", options: { fontFace: CODE, fontSize: 12 } },
    ],
    [
      { text: "M5\n(ASPLOS ’25)", options: { bold: true, color: NAVY } },
      { text: "Το hotness είναι sub-page — το πλήθος των accesses ανά page σε ξεγελάει", options: { color: NAVY } },
      { text: "Top-K trackers για pages (HPT) και για 64 B words (HWT)", options: { color: NAVY } },
      { text: "profiling 64 B\nmigration 4 KB", options: { fontFace: CODE, fontSize: 10.5, bold: true, color: NAVY } },
    ],
    [
      { text: "Memstrata\n(OSDI ’24)", options: { bold: true } },
      "Το hardware tiering δουλεύει — μέχρι να μπουν πολλές VMs και να συγκρουστούν",
      "Page coloring + online slowdown estimator",
      { text: "64 B (hardware)", options: { fontFace: CODE, fontSize: 11.5 } },
    ],
  ], [0.42, 0.82, 0.82, 0.82]);

  s.addText(
    [
      { text: "Οι τρεις διαγνώσεις διαφωνούν, και αυτό βοηθάει: ", options: { bold: true } },
      { text: "το NeoMem λέει ότι λείπει resolution στον χρόνο, το M5 ότι λείπει στον χώρο, και το Memstrata ότι το πρόβλημα βγαίνει μόνο όταν συνυπάρχουν πολλά workloads. Διαλέγω το M5, γιατί είναι πιο κοντά στην ιδέα του sub-page hotness.", options: {} },
    ],
    { x: ML, y: 5.5, w: CW, h: 1.1, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 22, align: "justify", margin: 0 }
  );

  s.addNotes("Το ότι διαφωνούν είναι δύναμη: δείχνει ότι διάβασα και τις τρεις, όχι μία.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 09 — The honest tradeoff
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(9, "§4.2", "4. Σχετικές εργασίες", "Ο τίμιος συμβιβασμός: pages ή lines;");

  caption(s, ML, 1.35, CW, "Πίνακας 4:", "page migration (software) vs line caching (hardware).");
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
      { text: "το line granularity κόβει το waste και το σταθερό κόστος, αλλά φέρνει conflict misses, tag storage, και χάνεις τη γρήγορη capacity σαν χρησιμοποιήσιμη μνήμη. Δεν είναι καθαρή νίκη, και γι’ αυτό δεν έχει κλείσει το θέμα.", options: {} },
    ],
    { x: ML, y: 5.7, w: CW, h: 1.0, fontFace: SERIF, fontSize: 14.5, color: INK, lineSpacing: 21, align: "justify", margin: 0 }
  );

  s.addNotes("Αυτή η διαφάνεια ξεχωρίζει το «διάβασα ένα paper» από το «κατάλαβα το πρόβλημα».");
}

// ═════════════════════════════════════════════════════════════════════════════
// 10 — The tool
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(10, "§5.1", "5. Μεθοδολογία", "Το εργαλείο: CXLRAMSim");

  s.addText(
    "Ο CXLRAMSim είναι full-system προσομοιωτής πάνω στο gem5 v25, που μπουτάρει Linux 6.14. Βάζει τη " +
    "συσκευή CXL στη σωστή θέση πάνω στο I/O bus, οπότε ο kernel, οι drivers και το software stack " +
    "μένουν αναλλοίωτα.",
    { x: ML, y: 1.45, w: CW, h: 0.9, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );

  s.addText("Τι μοντελοποιεί:", { x: ML, y: 2.45, w: CW, h: 0.32, fontFace: SERIF, fontSize: 14.5, bold: true, color: INK, margin: 0 });
  const comps = [
    ["Firmware.", "ACPI tables (MCFG, DSDT, CEDT, SRAT) για το discovery της τοπολογίας."],
    ["CXL.io.", "Root Complex και registers για το enumeration της συσκευής."],
    ["CXL.mem.", "transaction layer με M2S / S2M channels και packetization στα άκρα."],
    ["Coherence.", "MESI δύο επιπέδων με directory (Ruby)."],
  ];
  comps.forEach(([h, d], i) => {
    const y = 2.82 + i * 0.42;
    s.addText("–", { x: ML + 0.1, y, w: 0.3, h: 0.32, fontFace: SERIF, fontSize: 14.5, color: NAVY, margin: 0 });
    s.addText([{ text: h + " ", options: { bold: true, fontFace: CODE, fontSize: 12.5 } }, { text: d, options: {} }],
      { x: ML + 0.45, y, w: CW - 0.45, h: 0.34, fontFace: SERIF, fontSize: 14, color: INK, valign: "middle", margin: 0 });
  });

  block(s, ML, 4.75, CW, 1.75, "Πού μπαίνει ο δικός μου κώδικας",
    "Εκεί που ο CXL node κάνει de-packetize ένα M2S request σε access στη DRAM, έχω το triple " +
    "{physical address, read/write, timestamp}. Αυτό είναι ακριβώς το stream των LLC misses προς την " +
    "CXL που κάνουν profiling το NeoMem και το M5· τίποτα άλλο δεν φαίνεται από εκεί. Ο profiler μπαίνει " +
    "σαν tap πάνω σε αυτό το path.");

  s.addNotes("Ανοιχτό θέμα: χρειάζομαι πρόσβαση στο repo του CXLRAMSim — δεν βρήκα δημόσιο.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 11 — The experiment
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(11, "§5.2", "5. Μεθοδολογία", "Σχέδιο του πειράματος");

  s.addText("Πέντε cases για σύγκριση.", { x: ML, y: 1.42, w: 5.6, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  const arms = [
    ["Όλα στην CXL", "lower bound"],
    ["Όλα σε τοπική DRAM", "upper bound"],
    ["Απλό page migration", "το «πρόβλημα»"],
    ["Ο μηχανισμός του M5 (HPT + HWT)", "η πρόταση"],
    ["Oracle placement", "offline βέλτιστο"],
  ];
  arms.forEach(([a, tag], i) => {
    const y = 1.82 + i * 0.44;
    s.addText(`${i + 1}.`, { x: ML, y, w: 0.35, h: 0.3, fontFace: SERIF, fontSize: 14, color: NAVY, margin: 0 });
    s.addText([{ text: a, options: { bold: i === 2 || i === 3 } }, { text: "  — " + tag, options: { italic: true, color: MUT } }],
      { x: ML + 0.4, y, w: 5.5, h: 0.34, fontFace: SERIF, fontSize: 14, color: INK, valign: "middle", margin: 0 });
  });
  s.addText(
    "Η απόσταση ανάμεσα στο απλό migration και στο oracle είναι ακριβώς το πρόβλημα που θέλω να δείξω.",
    { x: ML, y: 4.15, w: 5.6, h: 0.7, fontFace: SERIF, fontSize: 14, italic: true, color: ALERT, lineSpacing: 20, align: "justify", margin: 0 }
  );

  s.addShape(pres.ShapeType.rect, { x: 6.75, y: 1.45, w: 0.01, h: 4.4, fill: { color: RULE } });

  s.addText("Workloads.", { x: 7.1, y: 1.42, w: 5.4, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  s.addText(
    [
      { text: "GUPS", options: { fontFace: CODE, fontSize: 12 } }, { text: " — τυχαία 8 B updates, μηδέν spatial locality (η χειρότερη περίπτωση)\n", options: {} },
      { text: "XSBench", options: { fontFace: CODE, fontSize: 12 } }, { text: " — Monte Carlo lookups σε μεγάλα tables\n", options: {} },
      { text: "PageRank", options: { fontFace: CODE, fontSize: 12 } }, { text: " — irregular graph access, το hot set μετακινείται\n", options: {} },
      { text: "Btree / YCSB-C", options: { fontFace: CODE, fontSize: 12 } }, { text: " — Zipf, ακραίο sub-page hotness", options: {} },
    ],
    { x: 7.1, y: 1.8, w: 5.4, h: 1.7, fontFace: SERIF, fontSize: 13.5, color: INK, lineSpacing: 20, margin: 0 }
  );

  s.addText("Metrics.", { x: 7.1, y: 3.85, w: 5.4, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  s.addText(
    [
      { text: "– CDF του access density ανά 64 B line\n", options: {} },
      { text: "– migration efficiency: bytes που μετακινήθηκαν ÷ bytes που όντως χρησιμοποιήθηκαν\n", options: {} },
      { text: "– promotion timeliness· πόσα pages είναι ακόμα hot την ώρα του promotion\n", options: {} },
      { text: "– slowdown vs το fast-tier ratio· αριθμός από ping-pongs", options: {} },
    ],
    { x: 7.1, y: 4.23, w: 5.4, h: 1.95, fontFace: SERIF, fontSize: 13, color: INK, lineSpacing: 19, margin: 0 }
  );

  s.addNotes("Πάντα αναφέρω και τα δύο bounds δίπλα σε κάθε case — αλλιώς το νούμερο δεν ερμηνεύεται.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 12 — The figure
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(12, "§5.3", "5. Μεθοδολογία", "Το σχήμα που θα το κρίνει");

  s.addText(
    "Για κάθε page 4 KB μετράω τι ποσοστό των accesses του πέφτει στις k πιο hot 64 B lines. Αν το 80% " +
    "των accesses πέφτει σε λιγότερο από 10% του page, το επιχείρημα του granularity αποδεικνύεται με ένα " +
    "μόνο γράφημα (Σχήμα 3).",
    { x: ML, y: 1.45, w: 5.15, h: 1.6, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 23, align: "justify", margin: 0 }
  );

  s.addText(
    [
      { text: "Επιφύλαξη. ", options: { bold: true, color: ALERT } },
      { text: "Η καμπύλη είναι το αναμενόμενο σχήμα, όχι πραγματικά δεδομένα· ο προσομοιωτής δεν έχει τρέξει ακόμα. Αν βγει επίπεδη, το επιχείρημα του sub-page hotness πέφτει για αυτό το workload — που είναι εξίσου χρήσιμο αποτέλεσμα.", options: {} },
    ],
    { x: ML, y: 3.25, w: 5.15, h: 1.9, fontFace: SERIF, fontSize: 14, color: INK, lineSpacing: 21, align: "justify", margin: 0 }
  );

  const cats = ["1", "4", "8", "16", "24", "32", "48", "64"];
  s.addChart(
    pres.ChartType.line,
    [
      { name: "Zipf (Btree / YCSB)", labels: cats, values: [31, 62, 78, 88, 93, 96, 99, 100] },
      { name: "Uniform (GUPS)", labels: cats, values: [2, 6, 13, 25, 38, 50, 75, 100] },
    ],
    {
      x: 6.35, y: 1.5, w: 6.13, h: 4.05,
      showTitle: false,
      chartColors: [NAVY, ALERT], lineSize: 2.25, lineSmooth: true,
      lineDash: ["solid", "dash"],
      showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: INK, legendFontFace: SERIF,
      catAxisTitle: "k πιο hot 64 B lines (από 64)", showCatAxisTitle: true, catAxisTitleFontSize: 11, catAxisTitleColor: MUT, catAxisTitleFontFace: SERIF,
      valAxisTitle: "cumulative %", showValAxisTitle: true, valAxisTitleFontSize: 11, valAxisTitleColor: MUT, valAxisTitleFontFace: SERIF,
      catAxisLabelColor: INK, valAxisLabelColor: INK, catAxisLabelFontFace: SERIF, valAxisLabelFontFace: SERIF,
      catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
      valAxisMaxVal: 100, valAxisMinVal: 0, valAxisMajorUnit: 25,
      valGridLine: { color: "E3E3E3", size: 1 }, catGridLine: { style: "none" },
    }
  );
  caption(s, 6.35, 5.65, 6.13, "Σχήμα 3:", "cumulative % των accesses στις k πιο hot 64 B lines (αναμενόμενο σχήμα).", "center");

  s.addNotes("Σκίτσο, όχι δεδομένα — και το δηλώνω. Ο Zipf δείχνει ακραία συγκέντρωση· το GUPS είναι το negative control.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 13 — Timeline
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(13, "§6.1", "6. Πλάνο & συζήτηση", "Φάσεις υλοποίησης και ρίσκο");

  const phases = [
    ["Φάση 1.", "Boot & checkpoint.", "Boot μέχρι shell, επιβεβαίωση του zNUMA node, latency microbenchmark («να δείξω ότι η CXL είναι όντως πιο αργή»)."],
    ["Φάση 2.", "Access tracing.", "Tap στο request stream της συσκευής και CDF του access density — το πρώτο πραγματικό αποτέλεσμα."],
    ["Φάση 3.", "Baseline migration.", "Απλό page migration με τίμιο cost model και bandwidth quota."],
    ["Φάση 4.", "Υλοποίηση του M5.", "Πρώτα ο HPT (hot pages), μετά ο HWT (hot 64 B words) σαν το κομμάτι που κάνει τη διαφορά."],
    ["Φάση 5.", "Evaluation & γράψιμο.", "Sensitivity ως προς K, interval, quota, CXL latency."],
  ];
  phases.forEach(([p, h, d], i) => {
    const y = 1.5 + i * 0.82;
    const hot = i === 1;
    s.addText(p, { x: ML, y, w: 1.15, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: hot ? ALERT : NAVY, margin: 0, valign: "top" });
    s.addText([{ text: h + " ", options: { bold: true, color: hot ? ALERT : INK } }, { text: d, options: {} }],
      { x: ML + 1.2, y, w: CW - 1.2, h: 0.7, fontFace: SERIF, fontSize: 14.5, color: INK, lineSpacing: 20, align: "justify", margin: 0, valign: "top" });
    if (i < 4) s.addShape(pres.ShapeType.rect, { x: ML + 1.2, y: y + 0.7, w: CW - 1.2, h: 0.006, fill: { color: "E8E8E8" } });
  });

  s.addText(
    "Η Φάση 2 μειώνει το ρίσκο όλων των υπολοίπων: βγάζει παρουσιάσιμο αποτέλεσμα πριν γραφτεί οποιοδήποτε " +
    "policy. Προαιρετικά: hardware cost model, latency sweep, δύο workloads μαζί.",
    { x: ML, y: 5.75, w: CW, h: 0.8, fontFace: SERIF, fontSize: 14, italic: true, color: MUT, lineSpacing: 21, align: "justify", margin: 0 }
  );

  s.addNotes("Δηλώνω ξεκάθαρα τι είναι core και τι stretch goal.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 14 — Open questions
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(14, "§6.2", "6. Πλάνο & συζήτηση", "Ανοιχτά ερωτήματα για συζήτηση");

  const qs = [
    ["Πρόσβαση στον CXLRAMSim.", "Υπάρχει repo και οδηγίες build; Ιδανικά και έτοιμο disk image — το να το χτίσω από το μηδέν είναι μέρες δουλειάς που δεν διδάσκουν κάτι για το tiering."],
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

  s.addNotes(
    "Έτοιμη απάντηση για «γιατί όχι κατευθείαν cache lines»: δεν υπάρχει PTE για line → hardware " +
    "indirection → Flat Memory Mode → κοστίζει conflict misses και capacity → αυτό ακριβώς λύνει το Memstrata."
  );
}

const out = path.join(__dirname, "..", "docs", "memory-tiering-cxl-gr.pptx");
pres.writeFile({ fileName: out }).then(() => console.log("wrote " + out));
