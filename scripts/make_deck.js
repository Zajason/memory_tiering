// Generates docs/memory-tiering-cxl-gr.pptx — concept presentation (Greek)
// Content follows docs/presentation-outline.md
//
// Visual system: "systems datasheet" — flat, no cards/shadows/badges. A grid of
// monospace coordinate tags (§NN, FIG.N, NN/14) is the repeated motif. Display
// type is large Cambria; all data/labels are Courier New; body is Calibri.
// Palette is amber (fast/hot tier) + teal (slow/CXL tier) on near-black ink,
// with light editorial slides between and one amber full-bleed close.
//
// Run: node scripts/make_deck.js

const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33" x 7.5" — must be set before adding slides
pres.author = "ntua-el23408";
pres.title = "Memory Tiering σε συστήματα CXL";

// ── Palette ──────────────────────────────────────────────────────────────────
const INK = "14181F"; // primary dark field
const INK2 = "1D242E"; // dark inset panel
const LINE_D = "313A46"; // hairline on dark
const PAPER = "EAEDF1"; // light field (cool, not cream)
const PANEL_L = "FFFFFF"; // light inset
const LINE_L = "D3D9E2"; // hairline on light

const FG = "E9ECF1"; // text on dark
const MUT_D = "8A95A3"; // muted on dark
const INKTX = "171C24"; // text on light
const MUT_L = "5C6675"; // muted on light

const AMBER = "F2A93B"; // fast / hot tier — primary accent
const AMBER_DK = "B0741A"; // amber readable on light
const TEAL = "5FB8A8"; // slow / CXL tier
const TEAL_DK = "2E7D6F"; // teal readable on light
const REDS = "E8604C"; // emphasis / warning

const DISP = "Cambria"; // display — full Greek coverage, true-width in QA
const MONO = "Courier New"; // tags, data, figure marks
const BODY = "Calibri"; // running text

const W = 13.33;
const ML = 0.8; // content left
const MR = 12.53; // content right
const CW = MR - ML; // content width = 11.73

// ── Helpers ──────────────────────────────────────────────────────────────────
function slide(mode) {
  const s = pres.addSlide();
  s._mode = mode;
  s.background = { color: mode === "dark" ? INK : mode === "amber" ? AMBER : PAPER };
  return s;
}
const isDark = (s) => s._mode === "dark";
const fg = (s) => (isDark(s) ? FG : INKTX);
const mut = (s) => (isDark(s) ? MUT_D : MUT_L);
const line = (s) => (isDark(s) ? LINE_D : LINE_L);
const panel = (s) => (isDark(s) ? INK2 : PANEL_L);
const amberOn = (s) => (isDark(s) ? AMBER : AMBER_DK);
const tealOn = (s) => (isDark(s) ? TEAL : TEAL_DK);

// Running head: the motif. §NN + section tag left, NN/14 right, in monospace.
function head(s, n, section) {
  const nn = String(n).padStart(2, "0");
  s.addText(
    [
      { text: `§${nn}`, options: { color: amberOn(s), bold: true } },
      { text: `   ${section}`, options: { color: mut(s) } },
    ],
    {
      x: ML, y: 0.52, w: CW - 1.4, h: 0.3,
      fontFace: MONO, fontSize: 12, charSpacing: 1, margin: 0, valign: "middle",
    }
  );
  s.addText(`${nn} / 14`, {
    x: MR - 1.4, y: 0.52, w: 1.4, h: 0.3,
    fontFace: MONO, fontSize: 12, color: mut(s), align: "right", margin: 0, valign: "middle",
  });
  // baseline tick — a short amber mark, not a full-width rule
  s.addShape(pres.ShapeType.rect, { x: ML, y: 0.9, w: 0.55, h: 0.028, fill: { color: amberOn(s) } });
}

// Big Cambria title, flush-left.
function title(s, text, y = 1.2, size = 34) {
  s.addText(text, {
    x: ML, y, w: CW, h: 0.72,
    fontFace: DISP, fontSize: size, bold: true, color: fg(s), lineSpacing: size * 1.06, margin: 0,
  });
}

// Flat horizontal meter bar with a monospace value label.
function meter(s, x, y, w, frac, color, label, labelColor) {
  s.addShape(pres.ShapeType.rect, { x, y, w, h: 0.2, fill: { color: line(s) } });
  s.addShape(pres.ShapeType.rect, { x, y, w: Math.max(0.02, w * frac), h: 0.2, fill: { color } });
  if (label) {
    s.addText(label, {
      x: x + w + 0.12, y: y - 0.08, w: 1.6, h: 0.36,
      fontFace: MONO, fontSize: 12, bold: true, color: labelColor || color, valign: "middle", margin: 0,
    });
  }
}

// Datasheet table with hairline rules and dark header row.
function sheet(s, x, y, w, colW, rows, opts = {}) {
  s.addTable(rows, {
    x, y, w, colW,
    fontFace: BODY, fontSize: opts.fs || 12.5, color: fg(s),
    fill: { color: panel(s) },
    border: { type: "solid", color: line(s), pt: 1 },
    valign: "middle",
    margin: [opts.pv || 0.07, 0.14, opts.pv || 0.07, 0.14],
    rowH: opts.rowH,
  });
}
function hcell(text, s) {
  return { text, options: { bold: true, color: isDark(s) ? INK : "FFFFFF", fill: { color: isDark(s) ? AMBER : INK }, fontFace: MONO, fontSize: 11.5 } };
}

// ═════════════════════════════════════════════════════════════════════════════
// 01 — Title
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("dark");
  s.addText("ΕΡΓΑΣΙΑ 02  ·  ΠΡΟΗΓΜΕΝΗ ΑΡΧΙΤΕΚΤΟΝΙΚΗ ΥΠΟΛΟΓΙΣΤΩΝ", {
    x: ML, y: 0.72, w: CW, h: 0.3,
    fontFace: MONO, fontSize: 12.5, color: AMBER, charSpacing: 1.5, margin: 0,
  });
  s.addShape(pres.ShapeType.rect, { x: ML, y: 1.12, w: 0.55, h: 0.03, fill: { color: AMBER } });

  s.addText("Memory Tiering\nσε συστήματα CXL", {
    x: ML, y: 1.85, w: 8.5, h: 2.3,
    fontFace: DISP, fontSize: 54, bold: true, color: FG, lineSpacing: 58, margin: 0,
  });

  s.addText(
    "Προσομοίωση τεχνικών ιεραρχικής διαχείρισης μνήμης με\nυποστήριξη υλικού, στον προσομοιωτή CXLRAMSim.",
    {
      x: ML, y: 4.35, w: 8.5, h: 0.9,
      fontFace: BODY, fontSize: 17, color: TEAL, lineSpacing: 25, margin: 0,
    }
  );

  // Two-tier schematic, drawn flat with monospace annotations
  const tx = 9.7, tw = 2.85;
  s.addText("ΔΥΟ ΒΑΘΜΙΔΕΣ", {
    x: tx, y: 1.9, w: tw, h: 0.3, fontFace: MONO, fontSize: 11, color: MUT_D, charSpacing: 1, margin: 0,
  });
  s.addShape(pres.ShapeType.rect, { x: tx, y: 2.3, w: tw, h: 0.85, fill: { color: AMBER } });
  s.addText("DDR", { x: tx + 0.2, y: 2.4, w: tw - 0.4, h: 0.4, fontFace: DISP, fontSize: 22, bold: true, color: INK, margin: 0 });
  s.addText("γρήγορη · μικρή", { x: tx + 0.2, y: 2.78, w: tw - 0.4, h: 0.3, fontFace: BODY, fontSize: 12, color: "5A4410", margin: 0 });
  s.addText("~80–100 ns", { x: tx, y: 3.18, w: tw, h: 0.28, fontFace: MONO, fontSize: 11.5, color: MUT_D, margin: 0 });

  s.addShape(pres.ShapeType.rect, { x: tx, y: 3.72, w: tw, h: 1.65, fill: { color: TEAL_DK } });
  s.addText("CXL", { x: tx + 0.2, y: 3.86, w: tw - 0.4, h: 0.4, fontFace: DISP, fontSize: 22, bold: true, color: "EAF6F3", margin: 0 });
  s.addText("αργή · μεγάλη", { x: tx + 0.2, y: 4.26, w: tw - 0.4, h: 0.3, fontFace: BODY, fontSize: 12, color: "CDE7E1", margin: 0 });
  s.addText("~250–400 ns  ·  2–3×", { x: tx, y: 5.4, w: tw, h: 0.28, fontFace: MONO, fontSize: 11.5, color: MUT_D, margin: 0 });

  s.addText("ntua-el23408  ·  github.com/Zajason/memory_tiering", {
    x: ML, y: 6.7, w: CW, h: 0.3, fontFace: MONO, fontSize: 11, color: MUT_D, margin: 0,
  });

  s.addNotes(
    "Στόχος: να δείξω ότι κατάλαβα το πρόβλημα και ότι έχω αξιόπιστο πλάνο. " +
    "Δεν έχω ακόμα αποτελέσματα — και το λέω ανοιχτά."
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// 02 — Motivation
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("light");
  head(s, 2, "ΚΙΝΗΤΡΟ");
  title(s, "Η μνήμη είναι ο περιοριστικός πόρος");

  s.addText(
    [
      { text: "Η DRAM είναι ακριβή και η χωρητικότητα ανά socket έχει φτάσει σε τοίχο — περιορισμένα DIMM slots, περιορισμένα pins DDR.", options: { breakLine: true, paraSpaceAfter: 12 } },
      { text: "Για περισσότερη μνήμη αγοράζεις περισσότερους επεξεργαστές που δεν χρειάζεσαι.", options: { breakLine: true, paraSpaceAfter: 12 } },
      { text: "Το CXL επιτρέπει επέκταση χωρητικότητας πάνω από τον δίαυλο PCIe, ανεξάρτητα από τους πυρήνες.", options: {} },
    ],
    {
      x: ML, y: 2.35, w: 6.6, h: 2.4,
      fontFace: BODY, fontSize: 15.5, color: INKTX, lineSpacing: 23, margin: 0, valign: "top",
    }
  );

  s.addText("ΤΟ ΠΡΟΒΛΗΜΑ ΣΕ ΑΡΙΘΜΟΥΣ", {
    x: ML, y: 4.95, w: 6.6, h: 0.3, fontFace: MONO, fontSize: 11.5, color: MUT_L, charSpacing: 1, margin: 0,
  });
  s.addText(
    "Σε στόλους cloud, μεγάλο μέρος της εγκατεστημένης DRAM μένει αναξιοποίητο («stranded») " +
    "επειδή οι πυρήνες του μηχανήματος έχουν ήδη πουληθεί.",
    {
      x: ML, y: 5.3, w: 6.6, h: 1.0, fontFace: BODY, fontSize: 14, color: INKTX, lineSpacing: 20, margin: 0,
    }
  );

  // Big statement numeral on a dark inset — flat, no card chrome
  s.addShape(pres.ShapeType.rect, { x: 7.9, y: 2.35, w: 4.63, h: 3.95, fill: { color: INK } });
  s.addText(
    [
      { text: "≈25", options: { fontSize: 110 } },
      { text: " %", options: { fontSize: 40 } },
    ],
    { x: 8.2, y: 2.7, w: 4.1, h: 1.75, fontFace: DISP, bold: true, color: AMBER, margin: 0, valign: "middle" }
  );
  s.addShape(pres.ShapeType.rect, { x: 8.2, y: 4.55, w: 0.55, h: 0.03, fill: { color: AMBER } });
  s.addText("της DRAM σε στόλο υπερκλίμακας\nπαραμένει «stranded»", {
    x: 8.2, y: 4.75, w: 4.05, h: 0.7, fontFace: BODY, fontSize: 15, color: FG, lineSpacing: 21, margin: 0,
  });
  s.addText("Azure — Pond, ASPLOS '23", {
    x: 8.2, y: 5.78, w: 4.05, h: 0.3, fontFace: MONO, fontSize: 10.5, color: MUT_D, margin: 0,
  });

  s.addNotes("Ένας αριθμός να μείνει: ~25% stranded DRAM. Το οικονομικό κίνητρο όλου του πεδίου.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 03 — What CXL costs
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("light");
  head(s, 3, "ΤΟ ΤΙΜΗΜΑ");
  title(s, "Τι κοστίζει πραγματικά η μνήμη CXL");

  sheet(s, ML, 2.15, 7.1, [3.0, 2.05, 2.05], [
    [hcell("Διαδρομή", s), hcell("Idle", s), hcell("Εύρος ζώνης", s)],
    ["Τοπική DDR5", { text: "~80–100 ns", options: { fontFace: MONO } }, "~30–50 GB/s / κανάλι"],
    ["Απομακρ. NUMA socket", { text: "~140–180 ns", options: { fontFace: MONO } }, "—"],
    [
      { text: "Μνήμη CXL (x8 Gen5)", options: { bold: true, color: AMBER_DK } },
      { text: "~250–400 ns", options: { bold: true, color: AMBER_DK, fontFace: MONO } },
      { text: "~25–30 GB/s", options: { bold: true, color: AMBER_DK } },
    ],
  ], { rowH: [0.42, 0.44, 0.44, 0.44] });

  s.addText("2–3×", {
    x: ML, y: 4.2, w: 1.7, h: 0.75, fontFace: DISP, fontSize: 44, bold: true, color: AMBER_DK, margin: 0,
  });
  s.addText(
    "μεγαλύτερη καθυστέρηση — ενώ η DRAM πάνω στην κάρτα είναι κανονική DDR5. " +
    "Το τίμημα είναι η διασύνδεση, όχι η μνήμη.",
    {
      x: ML + 1.85, y: 4.22, w: 5.25, h: 0.75, fontFace: BODY, fontSize: 13.5, color: INKTX, lineSpacing: 19, margin: 0, valign: "middle",
    }
  );

  s.addShape(pres.ShapeType.rect, { x: ML, y: 5.2, w: 7.1, h: 1.1, fill: { color: "F6E4D8" } });
  s.addText(
    "Συνέπεια: φόρτοι δεσμευμένοι από καθυστέρηση (pointer chasing) υποφέρουν· " +
    "φόρτοι δεσμευμένοι από εύρος ζώνης σχεδόν δεν το αντιλαμβάνονται.",
    {
      x: ML + 0.28, y: 5.35, w: 6.55, h: 0.8, fontFace: BODY, fontSize: 13, color: "6B3A1E", lineSpacing: 19, margin: 0, valign: "middle",
    }
  );

  // Request path as a monospace call-stack
  s.addShape(pres.ShapeType.rect, { x: 8.15, y: 2.15, w: 4.38, h: 4.15, fill: { color: INK } });
  s.addText("Η ΔΙΑΔΡΟΜΗ ΕΝΟΣ LOAD", {
    x: 8.4, y: 2.32, w: 3.9, h: 0.3, fontFace: MONO, fontSize: 11, color: MUT_D, charSpacing: 1, margin: 0,
  });
  const steps = [
    ["Πυρήνας CPU", TEAL], ["Αστοχία LLC", TEAL], ["CXL Root Complex", TEAL],
    ["Πακετοποίηση M2S", AMBER], ["Σύνδεσμος PCIe", AMBER], ["Ελεγκτής συσκευής", AMBER],
    ["DRAM στην κάρτα", TEAL],
  ];
  steps.forEach(([label, col], i) => {
    const y = 2.74 + i * 0.44;
    s.addText(`${String(i + 1).padStart(2, "0")}`, { x: 8.4, y, w: 0.4, h: 0.34, fontFace: MONO, fontSize: 12, bold: true, color: col, valign: "middle", margin: 0 });
    s.addText(label, { x: 8.85, y, w: 3.5, h: 0.34, fontFace: BODY, fontSize: 13, color: FG, valign: "middle", margin: 0 });
  });
  s.addText("↩ και όλη η διαδρομή αντίστροφα (S2M)", {
    x: 8.4, y: 5.86, w: 3.95, h: 0.32, fontFace: BODY, fontSize: 11.5, italic: true, color: MUT_D, margin: 0,
  });

  s.addNotes("Το σημείο: η DRAM στην κάρτα είναι κανονική DDR5. Η διασύνδεση είναι ο φόρος — γι' αυτό υπάρχει tiering.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 04 — The tiering problem stated  (dark)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("dark");
  head(s, 4, "ΔΙΑΤΥΠΩΣΗ");
  title(s, "Το πρόβλημα του tiering, με μια πρόταση");

  s.addText(
    "Δύο βαθμίδες μνήμης. Κράτα τα «θερμά» δεδομένα στη γρήγορη. Αν το πετύχεις, ένα μηχάνημα " +
    "με 25% τοπική DRAM αποδίδει σχεδόν σαν να είχε 100%.",
    {
      x: ML, y: 2.2, w: CW, h: 0.6, fontFace: BODY, fontSize: 16, color: TEAL, lineSpacing: 23, margin: 0,
    }
  );

  // Two verbs, flat split panels
  const pw = (CW - 0.4) / 2;
  s.addShape(pres.ShapeType.rect, { x: ML, y: 3.0, w: pw, h: 1.75, fill: { color: INK2 } });
  s.addText("↑", { x: ML + 0.3, y: 3.18, w: 0.7, h: 0.6, fontFace: DISP, fontSize: 30, bold: true, color: AMBER, margin: 0 });
  s.addText("ΠΡΟΑΓΩΓΗ", { x: ML + 1.05, y: 3.24, w: pw - 1.3, h: 0.4, fontFace: MONO, fontSize: 16, bold: true, color: AMBER, valign: "middle", margin: 0 });
  s.addText("Αργή → γρήγορη. Πρέπει να γίνει έγκαιρα: μια σελίδα που προάγεται αφού κρυώσει είναι καθαρή σπατάλη.", {
    x: ML + 0.3, y: 3.82, w: pw - 0.6, h: 0.85, fontFace: BODY, fontSize: 13.5, color: FG, lineSpacing: 19, margin: 0,
  });

  const x2 = ML + pw + 0.4;
  s.addShape(pres.ShapeType.rect, { x: x2, y: 3.0, w: pw, h: 1.75, fill: { color: INK2 } });
  s.addText("↓", { x: x2 + 0.3, y: 3.18, w: 0.7, h: 0.6, fontFace: DISP, fontSize: 30, bold: true, color: TEAL, margin: 0 });
  s.addText("ΥΠΟΒΑΘΜΙΣΗ", { x: x2 + 1.05, y: 3.24, w: pw - 1.3, h: 0.4, fontFace: MONO, fontSize: 16, bold: true, color: TEAL, valign: "middle", margin: 0 });
  s.addText("Γρήγορη → αργή. Πρέπει να είναι ασφαλής: η υποβάθμιση κάτι ακόμα θερμού προκαλεί ping-pong.", {
    x: x2 + 0.3, y: 3.82, w: pw - 0.6, h: 0.85, fontFace: BODY, fontSize: 13.5, color: FG, lineSpacing: 19, margin: 0,
  });

  s.addText("Η υποβάθμιση είναι εύκολη — μια προσέγγιση LRU αρκεί, και το Linux ήδη έχει LRU.", {
    x: ML, y: 5.2, w: CW, h: 0.35, fontFace: BODY, fontSize: 14.5, color: MUT_D, margin: 0,
  });
  s.addText("Η προαγωγή είναι το ανοιχτό πρόβλημα.", {
    x: ML, y: 5.62, w: CW, h: 0.5, fontFace: DISP, fontSize: 26, bold: true, color: AMBER, margin: 0,
  });
  s.addText("Το λέει η ίδια η κοινότητα του Linux MM, όχι εγώ.", {
    x: ML, y: 6.22, w: CW, h: 0.35, fontFace: BODY, fontSize: 13.5, italic: true, color: MUT_D, margin: 0,
  });

  s.addNotes("Γιατί δύσκολη η προαγωγή: απαιτεί να ξέρεις ότι μια σελίδα είναι θερμή ΤΩΡΑ — και αυτό κοστίζει.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 05 — Failure mode 1: profiling
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("light");
  head(s, 5, "ΑΣΤΟΧΙΑ 1 / 3  ·  PROFILING");
  title(s, "Γιατί αποτυγχάνει σήμερα: το profiling");

  sheet(s, ML, 2.1, CW, [2.55, 4.0, 5.18], [
    [hcell("Μηχανισμός", s), hcell("Πώς δουλεύει", s), hcell("Το μοιραίο ελάττωμα", s)],
    [
      { text: "PTE-scan · DAMON", options: { bold: true, fontFace: MONO, fontSize: 11.5 } },
      "Καθαρισμός και σάρωση των access bits των PTE",
      "1 bit = δυαδική πληροφορία. Η σάρωση κρατά δευτερόλεπτα — το θερμό σύνολο έχει ήδη αλλάξει",
    ],
    [
      { text: "hint faults · AutoNUMA · TPP", options: { bold: true, fontFace: MONO, fontSize: 11 } },
      "Σκόπιμη απο-χαρτογράφηση PTE ώστε η προσπέλαση να παγιδευτεί",
      { text: "Μετρά TLB misses, όχι LLC misses — τα δύο συσχετίζονται ασθενώς", options: { color: REDS } },
    ],
    [
      { text: "PEBS / IBS · Memtis", options: { bold: true, fontFace: MONO, fontSize: 11.5 } },
      "Δειγματοληψία της PMU σε αστοχίες LLC",
      "Το overhead ακολουθεί τον ρυθμό: >50% επιβράδυνση σε πυκνά δείγματα",
    ],
    [
      { text: "υλικό στη συσκευή CXL", options: { bold: true, fontFace: MONO, fontSize: 11.5, color: AMBER_DK } },
      { text: "Μετρητές μέσα στον ελεγκτή της συσκευής", options: { color: AMBER_DK } },
      { text: "Σωστό γεγονός, μηδενικό κόστος CPU — αλλά απαιτεί νέο υλικό", options: { color: AMBER_DK, bold: true } },
    ],
  ], { rowH: [0.42, 0.72, 0.72, 0.72, 0.72], fs: 12 });

  s.addShape(pres.ShapeType.rect, { x: ML, y: 5.7, w: CW, h: 0.85, fill: { color: INK } });
  s.addText(
    [
      { text: "Η ΚΡΙΣΙΜΗ ΛΕΠΤΟΜΕΡΕΙΑ  ", options: { bold: true, color: AMBER, fontFace: MONO, fontSize: 12 } },
      { text: "AutoNUMA και TPP μετρούν αστοχίες TLB, αλλά την κίνηση προς το CXL την καθορίζουν οι αστοχίες LLC. Βελτιστοποιούν λάθος σήμα.", options: { color: FG, fontFace: BODY, fontSize: 13.5 } },
    ],
    { x: ML + 0.28, y: 5.82, w: CW - 0.56, h: 0.6, lineSpacing: 19, margin: 0, valign: "middle" }
  );

  s.addNotes("Κοινός παρονομαστής: ακρίβεια × επικαιρότητα × overhead — διάλεξε δύο.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 06 — Failure mode 2: granularity  (dark, the central slide)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("dark");
  head(s, 6, "ΑΣΤΟΧΙΑ 2 / 3  ·  ΤΟ ΚΕΝΤΡΙΚΟ ΣΗΜΕΙΟ");
  title(s, "Γιατί αποτυγχάνει σήμερα: η κοκκομέτρηση");

  s.addText(
    "Η πυκνότητα προσπελάσεων μέσα σε μια σελίδα 4 KB είναι εξαιρετικά ανομοιόμορφη — " +
    "μια αναζήτηση σε hash table αγγίζει 64 bytes από τα 4096.",
    {
      x: ML, y: 2.0, w: CW, h: 0.55, fontFace: BODY, fontSize: 15.5, color: TEAL, lineSpacing: 22, margin: 0,
    }
  );

  // Scale spectrum: three big numerals with arrows, on dark, no cards
  const cols = [
    { x: ML, size: "64 B", label: "cache line", col: TEAL, pro: "Ελάχιστη σπατάλη μεταφοράς", con: "Τα μεταδεδομένα εκρήγνυνται· ο πίνακας σελίδων δεν το χαρτογραφεί" },
    { x: ML + 4.05, size: "4 KB", label: "προεπιλογή Linux", col: AMBER, pro: "Η μονάδα που ξέρει το OS", con: "Μέτρια και στα δύο: σπαταλά και κοστίζει" },
    { x: ML + 8.1, size: "2 MB", label: "huge page", col: REDS, pro: "Φθηνή μετανάστευση ανά byte", con: "Τεράστια σπατάλη: 99,99% της μεταφοράς μπορεί να είναι ψυχρό" },
  ];
  cols.forEach((c, i) => {
    s.addText(c.size, { x: c.x, y: 2.75, w: 3.5, h: 0.85, fontFace: DISP, fontSize: 52, bold: true, color: c.col, margin: 0 });
    s.addText(c.label, { x: c.x, y: 3.62, w: 3.5, h: 0.3, fontFace: MONO, fontSize: 12, color: MUT_D, margin: 0 });
    s.addText("+  " + c.pro, { x: c.x, y: 4.02, w: 3.6, h: 0.45, fontFace: BODY, fontSize: 12.5, color: FG, lineSpacing: 17, margin: 0 });
    s.addText("−  " + c.con, { x: c.x, y: 4.5, w: 3.6, h: 0.75, fontFace: BODY, fontSize: 12.5, color: MUT_D, lineSpacing: 17, margin: 0 });
    if (i < 2) {
      s.addText("→", { x: c.x + 3.6, y: 2.78, w: 0.45, h: 0.75, fontFace: DISP, fontSize: 30, color: MUT_D, align: "center", valign: "middle", margin: 0 });
    }
  });

  s.addShape(pres.ShapeType.rect, { x: ML, y: 5.4, w: CW, h: 1.1, fill: { color: AMBER } });
  s.addText("Δεν υπάρχει PTE για μια cache line.", {
    x: ML + 0.3, y: 5.5, w: CW - 0.6, h: 0.4, fontFace: DISP, fontSize: 20, bold: true, color: INK, margin: 0, valign: "middle",
  });
  s.addText(
    "Άρα δεν «μεταναστεύεις γραμμές αντί για σελίδες» μέσα από το λειτουργικό. Λύση: είτε έμμεση αναφορά σε υλικό " +
    "(η τοπική DRAM γίνεται cache), είτε — και εδώ στοχεύω — profiling σε λεπτή κοκκομέτρηση που οδηγεί αποφάσεις σε χονδρή.",
    {
      x: ML + 0.3, y: 5.94, w: CW - 0.6, h: 0.5, fontFace: BODY, fontSize: 13, color: "3A2A08", lineSpacing: 17, margin: 0, valign: "middle",
    }
  );

  s.addNotes(
    "Εδώ θα με ρωτήσουν. Απάντηση: κοκκομέτρηση profiling ≠ κοκκομέτρηση migration. " +
    "Το M5 κάνει profiling στα 64 B και migration στα 4 KB — δεν είναι συμβιβασμός, είναι ο σχεδιασμός."
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// 07 — Failure mode 3: migration cost
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("light");
  head(s, 7, "ΑΣΤΟΧΙΑ 3 / 3  ·  ΚΟΣΤΟΣ");
  title(s, "Γιατί αποτυγχάνει σήμερα: το κόστος μεταφοράς");

  s.addText("Τι πληρώνει ο πυρήνας για να προάγει μία σελίδα 4 KB", {
    x: ML, y: 2.12, w: 7.2, h: 0.3, fontFace: MONO, fontSize: 12, color: MUT_L, charSpacing: 0.5, margin: 0,
  });

  const costs = [
    ["Αντιγραφή", "4 KB ανάγνωση από CXL + 4 KB εγγραφή σε DDR — καταναλώνει το εύρος ζώνης που θέλεις να σώσεις"],
    ["Ενημέρωση πίνακα σελίδων", "Διάσχιση του rmap για κάθε PTE που χαρτογραφεί τη σελίδα"],
    ["TLB shootdown", "IPI σε κάθε πυρήνα με πιθανή cached μετάφραση — συνήθως το κυρίαρχο κόστος"],
    ["Ανταγωνισμός κλειδωμάτων", "mmap_lock, LRU locks — η μετανάστευση δεν παραλληλοποιείται καλά"],
  ];
  costs.forEach(([h, d], i) => {
    const y = 2.62 + i * 0.9;
    const hot = i === 2;
    s.addText(`0${i + 1}`, { x: ML, y, w: 0.55, h: 0.34, fontFace: DISP, fontSize: 22, bold: true, color: hot ? REDS : TEAL_DK, margin: 0 });
    s.addText(h, { x: ML + 0.65, y: y - 0.02, w: 6.6, h: 0.3, fontFace: BODY, fontSize: 14.5, bold: true, color: hot ? REDS : INKTX, margin: 0 });
    s.addText(d, { x: ML + 0.65, y: y + 0.3, w: 6.6, h: 0.5, fontFace: BODY, fontSize: 12, color: MUT_L, lineSpacing: 16, margin: 0 });
    if (i < 3) s.addShape(pres.ShapeType.rect, { x: ML + 0.65, y: y + 0.78, w: 6.6, h: 0.012, fill: { color: LINE_L } });
  });

  // µsec block, flat dark
  s.addShape(pres.ShapeType.rect, { x: 8.15, y: 2.62, w: 4.38, h: 3.55, fill: { color: INK } });
  s.addText("μs", { x: 8.4, y: 2.9, w: 3.9, h: 1.25, fontFace: DISP, fontSize: 82, bold: true, color: REDS, margin: 0 });
  s.addText("κόστος ανά μετανάστευση σελίδας", { x: 8.4, y: 4.2, w: 3.9, h: 0.3, fontFace: BODY, fontSize: 13.5, bold: true, color: FG, margin: 0 });
  s.addText("έναντι των ~250 ns που προσπαθείς να αποφύγεις", { x: 8.4, y: 4.54, w: 3.9, h: 0.5, fontFace: MONO, fontSize: 11.5, color: MUT_D, lineSpacing: 16, margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: 8.4, y: 5.1, w: 0.55, h: 0.028, fill: { color: REDS } });
  s.addText(
    "Μια σελίδα πρέπει να ξαναπροσπελαστεί πολλές φορές για να αποσβέσει τη μεταφορά της. " +
    "Γι' αυτό μια λάθος προαγωγή είναι ενεργά επιζήμια.",
    { x: 8.4, y: 5.26, w: 3.9, h: 0.85, fontFace: BODY, fontSize: 12.5, italic: true, color: FG, lineSpacing: 17, margin: 0 }
  );

  s.addNotes("Τάξη μεγέθους: μικροδευτερόλεπτα έναντι νανοδευτερολέπτων. Χιλιαπλάσιο κόστος.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 08 — Three papers, three diagnoses
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("light");
  head(s, 8, "Η ΒΙΒΛΙΟΓΡΑΦΙΑ");
  title(s, "Τρεις εργασίες, τρεις διαφορετικές διαγνώσεις");

  sheet(s, ML, 2.1, CW, [1.95, 4.05, 3.9, 1.83], [
    [hcell("Εργασία", s), hcell("Διάγνωση", s), hcell("Λύση", s), hcell("Κοκκομέτρηση", s)],
    [
      { text: "NeoMem\nMICRO '24", options: { bold: true, fontFace: MONO, fontSize: 11.5 } },
      "Το profiling είναι αργό και χονδροειδές — διόρθωσέ το και οι σελίδες 4 KB αρκούν",
      "Count-min sketch μέσα στον ελεγκτή CXL + δυναμικό κατώφλι θερμότητας",
      { text: "4 KB", options: { fontFace: MONO } },
    ],
    [
      { text: "M5\nASPLOS '25", options: { bold: true, fontFace: MONO, fontSize: 11.5, color: AMBER_DK } },
      { text: "Η θερμότητα είναι υπο-σελιδική — το πλήθος προσπελάσεων ανά σελίδα παραπλανά", options: { color: AMBER_DK } },
      { text: "Top-K trackers για σελίδες (HPT) και για λέξεις 64 B (HWT)", options: { color: AMBER_DK } },
      { text: "profiling 64 B\nmigration 4 KB", options: { bold: true, color: AMBER_DK, fontFace: MONO, fontSize: 11 } },
    ],
    [
      { text: "Memstrata\nOSDI '24", options: { bold: true, fontFace: MONO, fontSize: 11.5 } },
      "Το tiering σε υλικό δουλεύει — μέχρι να συνυπάρξουν πολλές VM και να συγκρουστούν",
      "Χρωματισμός σελίδων + online εκτιμητής επιβράδυνσης",
      { text: "64 B (υλικό)", options: { fontFace: MONO } },
    ],
  ], { rowH: [0.42, 0.82, 0.82, 0.82], fs: 12.5 });

  s.addShape(pres.ShapeType.rect, { x: ML, y: 5.55, w: CW, h: 0.95, fill: { color: INK } });
  s.addText(
    [
      { text: "Διαφωνούν μεταξύ τους — και αυτό είναι το ενδιαφέρον.  ", options: { bold: true, color: AMBER } },
      { text: "NeoMem → ανάλυση στον χρόνο.  M5 → ανάλυση στον χώρο.  Memstrata → το πρόβλημα εμφανίζεται μόνο υπό συστέγαση φόρτων.", options: { color: FG } },
    ],
    { x: ML + 0.28, y: 5.68, w: CW - 0.56, h: 0.7, fontFace: BODY, fontSize: 13.5, lineSpacing: 19, margin: 0, valign: "middle" }
  );

  s.addNotes("Το ότι διαφωνούν είναι δύναμη: δείχνει ότι διάβασα και τις τρεις, όχι μία.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 09 — The honest tradeoff  (dark ledger)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("dark");
  head(s, 9, "ΓΙΑΤΙ ΔΕΝ ΕΧΕΙ ΛΥΘΕΙ");
  title(s, "Ο έντιμος συμβιβασμός: σελίδες ή γραμμές;");

  const colA = 5.05, colB = 8.9, cwv = 3.5;
  s.addText("ΜΕΤΑΝΑΣΤΕΥΣΗ ΣΕΛΙΔΩΝ · OS", { x: colA, y: 2.0, w: cwv, h: 0.3, fontFace: MONO, fontSize: 11.5, bold: true, color: TEAL, margin: 0 });
  s.addText("CACHING ΓΡΑΜΜΩΝ · ΥΛΙΚΟ", { x: colB, y: 2.0, w: cwv, h: 0.3, fontFace: MONO, fontSize: 11.5, bold: true, color: AMBER, margin: 0 });

  const attrs = [
    ["Μονάδα", "4 KB / 2 MB", "64 B"],
    ["Ποιος αποφασίζει", "OS, με παλιά πληροφορία", "Υλικό, αντιδραστικά"],
    ["Χαμένη μεταφορά", "Υψηλή", "Σχεδόν μηδενική"],
    ["Σταθερό κόστος / κίνηση", "μs (TLB shootdown)", "ns"],
    ["Μεταδεδομένα", "Πίνακες σελίδων (υπάρχουν)", "Πίνακας ετικετών — τεράστιος"],
    ["Χωρητικότητα", "100% αξιοποιήσιμη", "Γρήγορη βαθμίδα → cache"],
    ["Αστοχίες σύγκρουσης", "Δεν υφίστανται", "Ναι — και μεταξύ ενοίκων"],
    ["Νέο υλικό", "Όχι", "Ναι"],
  ];
  const y0 = 2.42, rh = 0.44;
  attrs.forEach(([a, b, c], i) => {
    const y = y0 + i * rh;
    if (i % 2 === 0) s.addShape(pres.ShapeType.rect, { x: ML, y, w: CW, h: rh, fill: { color: INK2 } });
    s.addText(a, { x: ML + 0.2, y, w: colA - ML - 0.3, h: rh, fontFace: BODY, fontSize: 12.5, bold: true, color: FG, valign: "middle", margin: 0 });
    s.addText(b, { x: colA, y, w: cwv, h: rh, fontFace: BODY, fontSize: 12.5, color: MUT_D, valign: "middle", margin: 0 });
    s.addText(c, { x: colB, y, w: cwv + 0.3, h: rh, fontFace: BODY, fontSize: 12.5, color: MUT_D, valign: "middle", margin: 0 });
  });

  s.addText(
    "Η κοκκομέτρηση γραμμής εξαλείφει τη σπατάλη και το σταθερό κόστος — και αγοράζει αστοχίες σύγκρουσης, " +
    "αποθήκευση ετικετών και απώλεια της γρήγορης χωρητικότητας. Δεν είναι καθαρή νίκη.",
    { x: ML, y: 6.15, w: CW, h: 0.6, fontFace: DISP, fontSize: 14.5, bold: true, color: AMBER, lineSpacing: 20, margin: 0 }
  );

  s.addNotes("Αυτή η διαφάνεια ξεχωρίζει το «διάβασα μια εργασία» από το «κατάλαβα το πρόβλημα». Να μην κοπεί.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 10 — The tool
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("light");
  head(s, 10, "ΜΕΘΟΔΟΛΟΓΙΑ  ·  CXLRAMSim");
  title(s, "Το εργαλείο: CXLRAMSim");

  s.addText(
    "Πλήρης προσομοίωση συστήματος πάνω σε gem5 v25, με εκκίνηση Linux 6.14. Μοντελοποιεί τη συσκευή CXL " +
    "στη σωστή θέση πάνω στον δίαυλο I/O — άρα ο πυρήνας, οι οδηγοί και η στοίβα λογισμικού μένουν αναλλοίωτοι.",
    { x: ML, y: 2.1, w: CW, h: 0.7, fontFace: BODY, fontSize: 15, color: INKTX, lineSpacing: 22, margin: 0 }
  );

  const comps = [
    ["FIRMWARE", "Πίνακες ACPI: MCFG, DSDT, CEDT, SRAT για ανακάλυψη"],
    ["CXL.io", "Root Complex και σύνολα καταχωρητών για απαρίθμηση"],
    ["CXL.mem", "Επίπεδο συναλλαγών, κανάλια M2S / S2M"],
    ["ΣΥΝΟΧΗ", "MESI δύο επιπέδων, κατανεμημένος κατάλογος"],
  ];
  const cwc = (CW - 0.6) / 4;
  comps.forEach(([h, d], i) => {
    const x = ML + i * (cwc + 0.2);
    s.addText(h, { x, y: 3.0, w: cwc, h: 0.32, fontFace: MONO, fontSize: 13, bold: true, color: TEAL_DK, margin: 0 });
    s.addShape(pres.ShapeType.rect, { x, y: 3.36, w: 0.5, h: 0.026, fill: { color: TEAL_DK } });
    s.addText(d, { x, y: 3.5, w: cwc, h: 1.0, fontFace: BODY, fontSize: 12, color: MUT_L, lineSpacing: 16, margin: 0 });
  });

  s.addShape(pres.ShapeType.rect, { x: ML, y: 4.75, w: CW, h: 1.75, fill: { color: INK } });
  s.addText("ΠΟΥ ΜΠΑΙΝΕΙ Ο ΔΙΚΟΣ ΜΟΥ ΚΩΔΙΚΑΣ", { x: ML + 0.3, y: 4.92, w: CW - 0.6, h: 0.3, fontFace: MONO, fontSize: 12, bold: true, color: AMBER, charSpacing: 0.5, margin: 0 });
  s.addText(
    "Στο σημείο όπου ο κόμβος CXL απο-πακετοποιεί ένα αίτημα M2S σε προσπέλαση DRAM, έχω " +
    "{φυσική διεύθυνση, ανάγνωση/εγγραφή, χρονική στιγμή}.",
    { x: ML + 0.3, y: 5.28, w: CW - 0.6, h: 0.5, fontFace: BODY, fontSize: 13.5, color: FG, lineSpacing: 18, margin: 0 }
  );
  s.addText(
    "Αυτό είναι ακριβώς η ροή αστοχιών LLC προς το CXL που κάνουν profiling το NeoMem και το M5 — " +
    "δεν μπορείς να δεις τίποτε άλλο από εκεί. Ο profiler είναι μια λήψη πάνω σε αυτό το μονοπάτι.",
    { x: ML + 0.3, y: 5.82, w: CW - 0.6, h: 0.55, fontFace: BODY, fontSize: 13.5, color: TEAL, lineSpacing: 18, margin: 0 }
  );

  s.addNotes("Ανοιχτό θέμα: χρειάζομαι πρόσβαση στο αποθετήριο του CXLRAMSim — δεν βρήκα δημόσιο repo.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 11 — The experiment
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("light");
  head(s, 11, "ΣΧΕΔΙΟ ΑΞΙΟΛΟΓΗΣΗΣ");
  title(s, "Το πείραμα που αποδεικνύει το πρόβλημα");

  s.addText("ΠΕΝΤΕ ΣΚΕΛΗ ΣΥΓΚΡΙΣΗΣ", { x: ML, y: 2.1, w: 5.4, h: 0.3, fontFace: MONO, fontSize: 11.5, color: MUT_L, charSpacing: 0.5, margin: 0 });
  const arms = [
    ["Όλα σε CXL", "κάτω φράγμα", MUT_L, 0.18],
    ["Όλα σε τοπική DRAM", "άνω φράγμα", MUT_L, 1.0],
    ["Αφελής μετανάστευση σελίδων", "το «πρόβλημα»", REDS, 0.42],
    ["Σχήμα του M5 (HPT+HWT)", "η πρόταση", TEAL_DK, 0.78],
    ["Oracle τοποθέτηση", "βέλτιστο offline", MUT_L, 0.95],
  ];
  arms.forEach(([a, tag, col, frac], i) => {
    const y = 2.5 + i * 0.62;
    s.addText(a, { x: ML, y, w: 4.0, h: 0.3, fontFace: BODY, fontSize: 12.5, bold: col !== MUT_L, color: INKTX, margin: 0 });
    s.addText(tag, { x: ML, y: y + 0.28, w: 4.0, h: 0.24, fontFace: MONO, fontSize: 10, italic: true, color: col, margin: 0 });
    meter(s, ML + 4.15, y + 0.06, 1.7, frac, col === MUT_L ? "9AA4B2" : col);
  });
  s.addText("Η απόσταση αφελές ↔ oracle είναι το πρόβλημα που αναπαράγω.", {
    x: ML, y: 5.7, w: 5.9, h: 0.6, fontFace: DISP, fontSize: 14.5, bold: true, color: AMBER_DK, lineSpacing: 19, margin: 0,
  });

  s.addShape(pres.ShapeType.rect, { x: 6.9, y: 2.1, w: 0.014, h: 4.2, fill: { color: LINE_L } });

  s.addText("ΦΟΡΤΟΙ ΕΡΓΑΣΙΑΣ", { x: 7.25, y: 2.1, w: 5.3, h: 0.3, fontFace: MONO, fontSize: 11.5, color: MUT_L, charSpacing: 0.5, margin: 0 });
  s.addText(
    [
      { text: "GUPS — τυχαίες ενημερώσεις 8 B, μηδενική χωρική τοπικότητα· η αντίπαλη περίπτωση", options: { breakLine: true, paraSpaceAfter: 6 } },
      { text: "XSBench — αναζητήσεις Monte Carlo σε μεγάλους πίνακες", options: { breakLine: true, paraSpaceAfter: 6 } },
      { text: "PageRank — άτακτη προσπέλαση γράφου, μετακινούμενο θερμό σύνολο", options: { breakLine: true, paraSpaceAfter: 6 } },
      { text: "Btree / YCSB-C — λοξή κατανομή Zipf, ακραία υπο-σελιδική θερμότητα", options: {} },
    ],
    { x: 7.25, y: 2.46, w: 5.3, h: 1.75, fontFace: BODY, fontSize: 12.5, color: INKTX, lineSpacing: 17, margin: 0, valign: "top" }
  );

  s.addText("ΜΕΤΡΙΚΕΣ", { x: 7.25, y: 4.35, w: 5.3, h: 0.3, fontFace: MONO, fontSize: 11.5, color: MUT_L, charSpacing: 0.5, margin: 0 });
  s.addText(
    [
      { text: "Αθροιστική κατανομή πυκνότητας προσπελάσεων ανά γραμμή 64 B", options: { breakLine: true, paraSpaceAfter: 6 } },
      { text: "Απόδοση μεταφοράς: bytes που μεταφέρθηκαν ÷ bytes που χρησιμοποιήθηκαν", options: { breakLine: true, paraSpaceAfter: 6 } },
      { text: "Επικαιρότητα προαγωγής · ποσοστό σελίδων ακόμη θερμών κατά την προαγωγή", options: { breakLine: true, paraSpaceAfter: 6 } },
      { text: "Επιβράδυνση συναρτήσει του λόγου βαθμίδων · πλήθος ping-pong", options: {} },
    ],
    { x: 7.25, y: 4.71, w: 5.3, h: 1.78, fontFace: BODY, fontSize: 12.5, color: INKTX, lineSpacing: 17, margin: 0, valign: "top" }
  );

  s.addNotes("Πάντα αναφέρω και τα δύο φράγματα δίπλα σε κάθε σχήμα — αλλιώς το νούμερο δεν ερμηνεύεται.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 12 — The figure (native chart)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("light");
  head(s, 12, "ΤΟ ΖΗΤΟΥΜΕΝΟ ΑΠΟΤΕΛΕΣΜΑ");
  title(s, "Η εικόνα στην οποία κρίνεται η εργασία");

  s.addText("FIG. 01", { x: ML, y: 2.12, w: 5.2, h: 0.3, fontFace: MONO, fontSize: 12, bold: true, color: AMBER_DK, margin: 0 });
  s.addText(
    "Για κάθε σελίδα 4 KB: τι ποσοστό των προσπελάσεών της συγκεντρώνεται στις k θερμότερες γραμμές των 64 B; " +
    "Αν το 80% πέφτει σε λιγότερο από το 10% της σελίδας, το επιχείρημα της κοκκομέτρησης αποδεικνύεται σε ένα διάγραμμα.",
    { x: ML, y: 2.5, w: 5.15, h: 1.5, fontFace: BODY, fontSize: 13.5, color: INKTX, lineSpacing: 20, margin: 0 }
  );

  s.addShape(pres.ShapeType.rect, { x: ML, y: 4.15, w: 5.15, h: 1.15, fill: { color: "F6E4D8" } });
  s.addText("⚠ ΠΡΟΣΟΧΗ ΣΤΗΝ ΑΝΑΓΝΩΣΗ", { x: ML + 0.25, y: 4.28, w: 4.6, h: 0.3, fontFace: MONO, fontSize: 11.5, bold: true, color: "9A4A22", margin: 0 });
  s.addText("Η καμπύλη δίπλα είναι η αναμενόμενη μορφή, όχι μετρημένα δεδομένα. Δεν έχω τρέξει ακόμα τον προσομοιωτή.", {
    x: ML + 0.25, y: 4.6, w: 4.65, h: 0.62, fontFace: BODY, fontSize: 12, color: "6B3A1E", lineSpacing: 17, margin: 0,
  });

  s.addText("Αν η καμπύλη βγει επίπεδη, το επιχείρημα της υπο-σελιδικής θερμότητας καταρρέει για αυτόν τον φόρτο — εξίσου χρήσιμο.", {
    x: ML, y: 5.45, w: 5.15, h: 0.8, fontFace: BODY, fontSize: 12.5, italic: true, color: MUT_L, lineSpacing: 18, margin: 0,
  });

  const cats = ["1", "4", "8", "16", "24", "32", "48", "64"];
  s.addChart(
    pres.ChartType.line,
    [
      { name: "Zipf (Btree / YCSB)", labels: cats, values: [31, 62, 78, 88, 93, 96, 99, 100] },
      { name: "Ομοιόμορφη (GUPS)", labels: cats, values: [2, 6, 13, 25, 38, 50, 75, 100] },
    ],
    {
      x: 6.5, y: 2.15, w: 6.03, h: 4.3,
      showTitle: true, title: "Αθροιστικό % προσπελάσεων στις k θερμότερες γραμμές 64 B",
      titleFontSize: 12, titleColor: INKTX, titleFontFace: BODY,
      chartColors: [AMBER_DK, TEAL_DK], lineSize: 3, lineSmooth: true,
      showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: INKTX, legendFontFace: MONO,
      catAxisTitle: "k θερμότερες γραμμές 64 B (από 64)", showCatAxisTitle: true, catAxisTitleFontSize: 10, catAxisTitleColor: MUT_L,
      valAxisTitle: "αθροιστικό %", showValAxisTitle: true, valAxisTitleFontSize: 10, valAxisTitleColor: MUT_L,
      catAxisLabelColor: MUT_L, valAxisLabelColor: MUT_L, catAxisLabelFontFace: MONO, valAxisLabelFontFace: MONO,
      catAxisLabelFontSize: 10, valAxisLabelFontSize: 10,
      valAxisMaxVal: 100, valAxisMinVal: 0, valAxisMajorUnit: 25,
      valGridLine: { color: LINE_L, size: 1 }, catGridLine: { style: "none" },
    }
  );

  s.addNotes("Σκίτσο, όχι δεδομένα — και το δηλώνω. Ο Zipf δείχνει ακραία συγκέντρωση· το GUPS είναι αρνητικός έλεγχος.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 13 — Timeline
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("light");
  head(s, 13, "ΧΡΟΝΟΔΙΑΓΡΑΜΜΑ");
  title(s, "Φάσεις και διαχείριση ρίσκου");

  const phases = [
    ["Φ1", "Εκκίνηση & checkpoint", "Boot σε shell, επιβεβαίωση κόμβου zNUMA, microbenchmark: «απόδειξε ότι το CXL είναι αργό»"],
    ["Φ2", "Λήψη ιχνών προσπέλασης", "Σημείο λήψης στη ροή αιτημάτων· κατανομή πυκνότητας — πρώτο πραγματικό αποτέλεσμα"],
    ["Φ3", "Βασική γραμμή μεταφοράς", "Αφελής μετανάστευση σελίδων με έντιμο μοντέλο κόστους και ποσόστωση εύρους ζώνης"],
    ["Φ4", "Υλοποίηση M5", "Πρώτα το HPT, μετά το HWT ως το διαφοροποιητικό στοιχείο"],
    ["Φ5", "Αξιολόγηση & συγγραφή", "Ευαισθησία σε K, διάστημα, ποσόστωση, καθυστέρηση CXL"],
  ];
  phases.forEach(([p, h, d], i) => {
    const y = 2.2 + i * 0.82;
    const hot = i === 1;
    if (hot) s.addShape(pres.ShapeType.rect, { x: ML, y, w: CW, h: 0.72, fill: { color: "F6E4D8" } });
    s.addText(p, { x: ML + 0.2, y, w: 0.85, h: 0.72, fontFace: DISP, fontSize: 26, bold: true, color: hot ? REDS : TEAL_DK, valign: "middle", margin: 0 });
    s.addText(h, { x: ML + 1.15, y, w: 3.2, h: 0.72, fontFace: BODY, fontSize: 14, bold: true, color: INKTX, valign: "middle", margin: 0 });
    s.addText(d, { x: ML + 4.5, y, w: 7.15, h: 0.72, fontFace: BODY, fontSize: 12, color: MUT_L, valign: "middle", lineSpacing: 16, margin: 0 });
    if (i < 4 && !hot) s.addShape(pres.ShapeType.rect, { x: ML + 1.15, y: y + 0.72, w: CW - 1.15, h: 0.01, fill: { color: LINE_L } });
  });

  s.addText(
    "Η Φ2 απομειώνει το ρίσκο όλων των υπολοίπων: παράγει παρουσιάσιμο αποτέλεσμα πριν γραφτεί οποιαδήποτε πολιτική. " +
    "Προαιρετικά: μοντέλο κόστους υλικού, σάρωση καθυστέρησης, δύο ταυτόχρονοι φόρτοι.",
    { x: ML, y: 6.45, w: CW, h: 0.6, fontFace: BODY, fontSize: 12, italic: true, color: MUT_L, lineSpacing: 17, margin: 0 }
  );

  s.addNotes("Δηλώνω ξεκάθαρα τι είναι βασικό και τι stretch goal.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 14 — Open questions  (amber full-bleed close)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = slide("amber");
  s.addText("§14   ΠΡΟΣ ΣΥΖΗΤΗΣΗ", {
    x: ML, y: 0.6, w: CW - 1.4, h: 0.3, fontFace: MONO, fontSize: 12.5, bold: true, color: INK, charSpacing: 1, margin: 0,
  });
  s.addText("14 / 14", { x: MR - 1.4, y: 0.6, w: 1.4, h: 0.3, fontFace: MONO, fontSize: 12, color: "6B4E12", align: "right", margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: ML, y: 0.98, w: 0.55, h: 0.03, fill: { color: INK } });

  s.addText("Ανοιχτά ερωτήματα προς εσάς", {
    x: ML, y: 1.35, w: CW, h: 0.8, fontFace: DISP, fontSize: 38, bold: true, color: INK, margin: 0,
  });

  const qs = [
    ["Πρόσβαση στο CXLRAMSim", "Υπάρχει αποθετήριο και οδηγίες build; Ιδανικά και έτοιμο disk image — το χτίσιμο από το μηδέν είναι παράκαμψη ημερών."],
    ["Κλίμακα φόρτων", "Αποδεκτό να κατεβάσω το μέγεθος σε εκατοντάδες MB αντί 10–20 GB RSS, κρατώντας ρεαλιστικό τον λόγο των βαθμίδων;"],
    ["Εύρος υλοποίησης", "Αρκεί profiler HPT+HWT με μοντελοποιημένη μηχανή μεταφοράς, ή θέλετε πραγματική μετανάστευση Linux από kernel module;"],
    ["Επιλογή εργασίας", "Είναι το M5 η σωστή επιλογή, ή προτιμάτε να δείτε NeoMem;"],
  ];
  qs.forEach(([h, d], i) => {
    const y = 2.5 + i * 1.02;
    s.addText(`0${i + 1}`, { x: ML, y, w: 0.7, h: 0.8, fontFace: DISP, fontSize: 30, bold: true, color: "6B4E12", margin: 0 });
    s.addText(h, { x: ML + 0.85, y: y - 0.02, w: 11, h: 0.32, fontFace: MONO, fontSize: 14, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: ML + 0.85, y: y + 0.32, w: 11, h: 0.5, fontFace: BODY, fontSize: 13, color: "3A2A08", lineSpacing: 17, margin: 0 });
    if (i < 3) s.addShape(pres.ShapeType.rect, { x: ML + 0.85, y: y + 0.86, w: 11, h: 0.012, fill: { color: "D9992E" } });
  });

  s.addText("github.com/Zajason/memory_tiering", {
    x: ML, y: 6.9, w: CW, h: 0.3, fontFace: MONO, fontSize: 11.5, color: "6B4E12", margin: 0,
  });

  s.addNotes(
    "Το να ρωτάω ανοιχτά είναι δύναμη. Έτοιμη απάντηση για «γιατί όχι απευθείας cache lines»: " +
    "δεν υπάρχει PTE για γραμμή → έμμεση αναφορά σε υλικό → Flat Memory Mode → κοστίζει αστοχίες " +
    "σύγκρουσης και χωρητικότητα → αυτό ακριβώς λύνει το Memstrata."
  );
}

const out = path.join(__dirname, "..", "docs", "memory-tiering-cxl-gr.pptx");
pres.writeFile({ fileName: out }).then(() => console.log("wrote " + out));
