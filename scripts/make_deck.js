// Generates docs/memory-tiering-cxl-gr.pptx — concept presentation (Greek)
// Content follows docs/presentation-outline.md
// Run: node scripts/make_deck.js

const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3" x 7.5" — must be set before adding slides
pres.author = "ntua-el23408";
pres.title = "Memory Tiering σε συστήματα CXL";

// ── Palette ────────────────────────────────────────────────────────────────
// Thermal metaphor, matched to the topic: coral = hot data / fast tier,
// ice blue = cold data / slow CXL tier. Carried across every slide.
const INK = "0F1729"; // dark background
const INK2 = "1B2540"; // dark card
const HOT = "F9615F"; // coral — hot / fast tier
const AMBER = "F5A623"; // secondary warm accent
const ICE = "8FBEDC"; // ice blue — cold / CXL tier
const ICEDK = "3E6B8C"; // ice blue, readable on light bg
const CREAM = "F7F9FC"; // light background
const CARD = "FFFFFF";
const MUTED = "6B7A90";
const TXT = "1A2233";
const WHITE = "FFFFFF";

const HEAD = "Cambria"; // Greek coverage, renders true-to-width
const BODY = "Calibri";

const W = 13.3;
const M = 0.6; // slide margin

// ── Helpers ────────────────────────────────────────────────────────────────
function lightSlide() {
  const s = pres.addSlide();
  s.background = { color: CREAM };
  return s;
}

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: INK };
  return s;
}

// Title for a light content slide. Optional kicker above it.
function title(s, text, kicker) {
  if (kicker) {
    s.addText(kicker, {
      x: M, y: 0.36, w: W - 2 * M, h: 0.3,
      fontFace: BODY, fontSize: 13, bold: true, color: HOT,
      charSpacing: 1.4, margin: 0,
    });
  }
  s.addText(text, {
    x: M, y: kicker ? 0.68 : 0.5, w: W - 2 * M, h: 0.75,
    fontFace: HEAD, fontSize: 32, bold: true, color: TXT, margin: 0,
  });
}

// Numbered circle used as the repeated visual motif on content slides.
function badge(s, n, x, y, color = HOT, size = 0.44) {
  s.addShape(pres.ShapeType.ellipse, {
    x, y, w: size, h: size, fill: { color },
  });
  s.addText(String(n), {
    x, y, w: size, h: size,
    fontFace: BODY, fontSize: 14, bold: true, color: WHITE,
    align: "center", valign: "middle", margin: 0,
  });
}

function card(s, opts) {
  s.addShape(pres.ShapeType.roundRect, {
    x: opts.x, y: opts.y, w: opts.w, h: opts.h,
    fill: { color: opts.fill || CARD },
    rectRadius: 0.06,
    line: { color: opts.line || "E3E9F2", width: 1 },
    shadow: { type: "outer", color: "8494AB", opacity: 0.16, blur: 10, offset: 2, angle: 90 },
  });
}

// ───────────────────────────────────────────────────────────────────────────
// 1 — Title
// ───────────────────────────────────────────────────────────────────────────
{
  const s = darkSlide();

  s.addText("ΕΡΓΑΣΙΑ 2", {
    x: M, y: 1.5, w: 8, h: 0.3,
    fontFace: BODY, fontSize: 14, bold: true, color: HOT, charSpacing: 2.5, margin: 0,
  });

  s.addText("Memory Tiering σε\nσυστήματα CXL", {
    x: M, y: 1.95, w: 8.4, h: 1.9,
    fontFace: HEAD, fontSize: 44, bold: true, color: WHITE, lineSpacing: 50, margin: 0,
  });

  s.addText(
    "Προσομοίωση τεχνικών ιεραρχικής διαχείρισης μνήμης\nμε υποστήριξη υλικού, στον προσομοιωτή CXLRAMSim",
    {
      x: M, y: 4.05, w: 8.4, h: 0.9,
      fontFace: BODY, fontSize: 16, color: ICE, lineSpacing: 24, margin: 0,
    }
  );

  s.addText("Προηγμένη Αρχιτεκτονική Υπολογιστών  ·  ΕΜΠ  ·  Παρουσίαση ιδέας", {
    x: M, y: 5.35, w: 8.4, h: 0.3,
    fontFace: BODY, fontSize: 12, color: MUTED, margin: 0,
  });

  // Visual: the two tiers, as a stacked pair of bars
  const bx = 9.5;
  s.addShape(pres.ShapeType.roundRect, {
    x: bx, y: 2.15, w: 3.0, h: 0.95, fill: { color: HOT }, rectRadius: 0.05,
  });
  s.addText("DDR  ·  γρήγορη  ·  μικρή", {
    x: bx, y: 2.15, w: 3.0, h: 0.95,
    fontFace: BODY, fontSize: 13, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0,
  });
  s.addText("~80–100 ns", {
    x: bx, y: 3.16, w: 3.0, h: 0.28,
    fontFace: BODY, fontSize: 11, color: MUTED, align: "center", margin: 0,
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: bx, y: 3.62, w: 3.0, h: 1.85, fill: { color: ICEDK }, rectRadius: 0.05,
  });
  s.addText("CXL  ·  αργή  ·  μεγάλη", {
    x: bx, y: 3.62, w: 3.0, h: 1.85,
    fontFace: BODY, fontSize: 13, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0,
  });
  s.addText("~250–400 ns", {
    x: bx, y: 5.53, w: 3.0, h: 0.28,
    fontFace: BODY, fontSize: 11, color: MUTED, align: "center", margin: 0,
  });

  s.addNotes(
    "Στόχος: να δείξω ότι κατάλαβα το πρόβλημα και ότι έχω αξιόπιστο πλάνο. " +
    "Δεν έχω ακόμα αποτελέσματα — και το λέω ανοιχτά."
  );
}

// ───────────────────────────────────────────────────────────────────────────
// 2 — Motivation
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Η μνήμη είναι ο περιοριστικός πόρος", "ΚΙΝΗΤΡΟ");

  s.addText(
    [
      { text: "Η DRAM είναι ακριβή και η χωρητικότητα ανά socket έχει φτάσει σε τοίχο: περιορισμένα DIMM slots, περιορισμένα pins DDR.", options: { bullet: true, breakLine: true } },
      { text: "Για περισσότερη μνήμη αγοράζεις περισσότερους επεξεργαστές που δεν χρειάζεσαι.", options: { bullet: true, breakLine: true } },
      { text: "Το CXL επιτρέπει την επέκταση χωρητικότητας πάνω από τον δίαυλο PCIe, ανεξάρτητα από τους πυρήνες.", options: { bullet: true } },
    ],
    {
      x: M, y: 1.85, w: 7.2, h: 2.2,
      fontFace: BODY, fontSize: 15, color: TXT, lineSpacing: 22, paraSpaceAfter: 10, margin: 0,
    }
  );

  card(s, { x: M, y: 4.25, w: 7.2, h: 1.55 });
  s.addText("Το πρόβλημα σε αριθμούς", {
    x: M + 0.35, y: 4.45, w: 6.5, h: 0.3,
    fontFace: BODY, fontSize: 13, bold: true, color: MUTED, margin: 0,
  });
  s.addText(
    "Σε στόλους cloud, μεγάλο μέρος της εγκατεστημένης DRAM μένει αναξιοποίητο " +
    "(«stranded») επειδή οι πυρήνες του μηχανήματος έχουν ήδη πουληθεί.",
    {
      x: M + 0.35, y: 4.8, w: 6.5, h: 0.85,
      fontFace: BODY, fontSize: 13.5, color: TXT, lineSpacing: 19, margin: 0,
    }
  );

  // Big stat callout
  card(s, { x: 8.3, y: 1.85, w: 4.4, h: 3.95 });
  s.addText("~25%", {
    x: 8.5, y: 2.55, w: 4.0, h: 1.3,
    fontFace: HEAD, fontSize: 72, bold: true, color: HOT, align: "center", margin: 0,
  });
  s.addText("της DRAM σε στόλο υπερκλίμακας\nπαραμένει «stranded»", {
    x: 8.5, y: 3.9, w: 4.0, h: 0.8,
    fontFace: BODY, fontSize: 14, color: TXT, align: "center", lineSpacing: 20, margin: 0,
  });
  s.addText("Azure — αναφορά στο Pond, ASPLOS '23", {
    x: 8.5, y: 4.85, w: 4.0, h: 0.5,
    fontFace: BODY, fontSize: 11, italic: true, color: MUTED, align: "center", margin: 0,
  });

  s.addNotes("Ένας αριθμός να μείνει: ~25% stranded DRAM. Αυτό είναι το οικονομικό κίνητρο όλου του πεδίου.");
}

// ───────────────────────────────────────────────────────────────────────────
// 3 — What CXL costs
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Τι κοστίζει πραγματικά η μνήμη CXL", "ΤΟ ΤΙΜΗΜΑ");

  const rows = [
    [
      { text: "Διαδρομή", options: { bold: true, color: WHITE, fill: { color: INK }, fontSize: 13 } },
      { text: "Καθυστέρηση (idle)", options: { bold: true, color: WHITE, fill: { color: INK }, fontSize: 13 } },
      { text: "Εύρος ζώνης", options: { bold: true, color: WHITE, fill: { color: INK }, fontSize: 13 } },
    ],
    ["Τοπική DDR5", "~80–100 ns", "~30–50 GB/s ανά κανάλι"],
    ["Απομακρυσμένο NUMA socket", "~140–180 ns", "—"],
    [
      { text: "Μνήμη CXL (x8 Gen5)", options: { bold: true, color: HOT } },
      { text: "~250–400 ns", options: { bold: true, color: HOT } },
      { text: "~25–30 GB/s", options: { bold: true, color: HOT } },
    ],
  ];

  s.addTable(rows, {
    x: M, y: 1.9, w: 7.2,
    colW: [3.0, 2.1, 2.1],
    rowH: [0.42, 0.4, 0.4, 0.4],
    fontFace: BODY, fontSize: 13, color: TXT,
    fill: { color: CARD },
    border: { type: "solid", color: "E3E9F2", pt: 1 },
    valign: "middle",
    margin: [0, 0.12, 0, 0.12],
  });

  s.addText("2–3×", {
    x: M, y: 3.85, w: 1.4, h: 0.7,
    fontFace: HEAD, fontSize: 40, bold: true, color: HOT, margin: 0,
  });
  s.addText(
    "μεγαλύτερη καθυστέρηση — ενώ η DRAM πάνω στην κάρτα είναι\nκανονική DDR5. Το τίμημα είναι η διασύνδεση, όχι η μνήμη.",
    {
      x: M + 1.5, y: 3.9, w: 5.7, h: 0.7,
      fontFace: BODY, fontSize: 13.5, color: TXT, lineSpacing: 19, margin: 0,
    }
  );

  card(s, { x: M, y: 4.85, w: 7.2, h: 1.05, fill: "FDF0EF", line: "F6C9C7" });
  s.addText(
    "Συνέπεια: φόρτοι δεσμευμένοι από καθυστέρηση (pointer chasing) υποφέρουν· " +
    "φόρτοι δεσμευμένοι από εύρος ζώνης σχεδόν δεν το αντιλαμβάνονται.",
    {
      x: M + 0.3, y: 5.0, w: 6.6, h: 0.75,
      fontFace: BODY, fontSize: 13, color: TXT, lineSpacing: 19, margin: 0,
    }
  );

  // Request path
  card(s, { x: 8.3, y: 1.9, w: 4.4, h: 4.0 });
  s.addText("Η διαδρομή ενός load", {
    x: 8.55, y: 2.08, w: 3.9, h: 0.3,
    fontFace: BODY, fontSize: 13, bold: true, color: MUTED, margin: 0,
  });

  const steps = [
    ["Πυρήνας CPU", ICEDK],
    ["Αστοχία LLC", ICEDK],
    ["CXL Root Complex", ICEDK],
    ["Πακετοποίηση M2S", HOT],
    ["Σύνδεσμος PCIe", HOT],
    ["Ελεγκτής συσκευής", HOT],
    ["DRAM στην κάρτα", ICEDK],
  ];
  steps.forEach(([label, col], i) => {
    const y = 2.5 + i * 0.44;
    s.addShape(pres.ShapeType.ellipse, { x: 8.6, y: y + 0.08, w: 0.16, h: 0.16, fill: { color: col } });
    s.addText(label, {
      x: 8.92, y, w: 3.5, h: 0.34,
      fontFace: BODY, fontSize: 12.5, color: TXT, valign: "middle", margin: 0,
    });
  });
  s.addText("…και όλη η διαδρομή αντίστροφα (S2M)", {
    x: 8.55, y: 5.5, w: 3.9, h: 0.32,
    fontFace: BODY, fontSize: 11.5, italic: true, color: MUTED, margin: 0,
  });

  s.addNotes("Το σημείο: η DRAM στην κάρτα είναι κανονική DDR5. Η διασύνδεση είναι ο φόρος. Γι' αυτό υπάρχει tiering.");
}

// ───────────────────────────────────────────────────────────────────────────
// 4 — The tiering problem stated
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Το πρόβλημα του tiering, με μια πρόταση", "ΔΙΑΤΥΠΩΣΗ");

  s.addText(
    "Δύο βαθμίδες μνήμης. Κράτα τα «θερμά» δεδομένα στη γρήγορη. " +
    "Αν το πετύχεις, ένα μηχάνημα με 25% τοπική DRAM αποδίδει σχεδόν σαν να είχε 100%.",
    {
      x: M, y: 1.8, w: 12.1, h: 0.6,
      fontFace: BODY, fontSize: 15, color: TXT, lineSpacing: 21, margin: 0,
    }
  );

  // Two verbs
  card(s, { x: M, y: 2.65, w: 5.9, h: 1.75 });
  badge(s, "↑", M + 0.35, 2.95, HOT);
  s.addText("Προαγωγή (promotion)", {
    x: M + 0.95, y: 2.97, w: 4.6, h: 0.35,
    fontFace: BODY, fontSize: 16, bold: true, color: TXT, valign: "middle", margin: 0,
  });
  s.addText(
    "Αργή → γρήγορη. Πρέπει να γίνει έγκαιρα: μια σελίδα που προάγεται " +
    "αφού κρυώσει είναι καθαρή σπατάλη.",
    {
      x: M + 0.35, y: 3.5, w: 5.2, h: 0.8,
      fontFace: BODY, fontSize: 13, color: TXT, lineSpacing: 19, margin: 0,
    }
  );

  card(s, { x: 6.8, y: 2.65, w: 5.9, h: 1.75 });
  badge(s, "↓", 7.15, 2.95, ICEDK);
  s.addText("Υποβάθμιση (demotion)", {
    x: 7.75, y: 2.97, w: 4.6, h: 0.35,
    fontFace: BODY, fontSize: 16, bold: true, color: TXT, valign: "middle", margin: 0,
  });
  s.addText(
    "Γρήγορη → αργή. Πρέπει να είναι ασφαλής: η υποβάθμιση κάτι " +
    "ακόμα θερμού προκαλεί ping-pong.",
    {
      x: 7.15, y: 3.5, w: 5.2, h: 0.8,
      fontFace: BODY, fontSize: 13, color: TXT, lineSpacing: 19, margin: 0,
    }
  );

  card(s, { x: M, y: 4.7, w: 12.1, h: 1.35, fill: INK2, line: INK2 });
  s.addText("Η υποβάθμιση είναι εύκολη — μια προσέγγιση LRU αρκεί, και το Linux ήδη έχει LRU.", {
    x: M + 0.4, y: 4.9, w: 11.3, h: 0.35,
    fontFace: BODY, fontSize: 14, color: ICE, margin: 0,
  });
  s.addText(
    "Η προαγωγή είναι το ανοιχτό πρόβλημα — και αυτό το λέει η ίδια η κοινότητα του Linux MM, όχι εγώ.",
    {
      x: M + 0.4, y: 5.3, w: 11.3, h: 0.4,
      fontFace: BODY, fontSize: 15, bold: true, color: WHITE, margin: 0,
    }
  );

  s.addNotes("Γιατί είναι δύσκολη η προαγωγή: απαιτεί να ξέρεις ότι μια σελίδα είναι θερμή ΤΩΡΑ — και αυτό κοστίζει.");
}

// ───────────────────────────────────────────────────────────────────────────
// 5 — Failure mode 1: profiling
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Γιατί αποτυγχάνει σήμερα: το profiling", "ΑΣΤΟΧΙΑ 1 ΑΠΟ 3");

  const rows = [
    [
      { text: "Μηχανισμός", options: { bold: true, color: WHITE, fill: { color: INK }, fontSize: 13 } },
      { text: "Πώς δουλεύει", options: { bold: true, color: WHITE, fill: { color: INK }, fontSize: 13 } },
      { text: "Το μοιραίο ελάττωμα", options: { bold: true, color: WHITE, fill: { color: INK }, fontSize: 13 } },
    ],
    [
      { text: "PTE-scan\n(DAMON)", options: { bold: true } },
      "Καθαρισμός και σάρωση των access bits των PTE",
      "1 bit = δυαδική πληροφορία. Η σάρωση κρατά δευτερόλεπτα — το θερμό σύνολο έχει ήδη αλλάξει",
    ],
    [
      { text: "Hint faults\n(AutoNUMA, TPP)", options: { bold: true } },
      "Σκόπιμη απο-χαρτογράφηση PTE ώστε η προσπέλαση να παγιδευτεί",
      "Μετρά TLB misses, όχι LLC misses — και τα δύο συσχετίζονται ασθενώς",
    ],
    [
      { text: "PEBS / IBS\n(Memtis)", options: { bold: true } },
      "Δειγματοληψία της PMU σε αστοχίες LLC",
      "Το overhead ακολουθεί τον ρυθμό δειγματοληψίας: >50% επιβράδυνση σε πυκνά δείγματα",
    ],
    [
      { text: "Υλικό στη συσκευή CXL", options: { bold: true, color: HOT } },
      { text: "Μετρητές μέσα στον ελεγκτή της συσκευής", options: { color: HOT } },
      { text: "Σωστό γεγονός, μηδενικό κόστος CPU — αλλά απαιτεί νέο υλικό", options: { color: HOT, bold: true } },
    ],
  ];

  s.addTable(rows, {
    x: M, y: 1.9, w: 12.1,
    colW: [2.5, 3.9, 5.7],
    fontFace: BODY, fontSize: 12.5, color: TXT,
    fill: { color: CARD },
    border: { type: "solid", color: "E3E9F2", pt: 1 },
    valign: "middle",
    margin: [0.06, 0.12, 0.06, 0.12],
  });

  card(s, { x: M, y: 5.4, w: 12.1, h: 1.05, fill: "FDF0EF", line: "F6C9C7" });
  s.addText(
    [
      { text: "Η κρίσιμη λεπτομέρεια:  ", options: { bold: true, color: HOT } },
      { text: "AutoNUMA και TPP μετρούν αστοχίες TLB, αλλά την κίνηση προς το CXL την καθορίζουν οι αστοχίες LLC. Βελτιστοποιούν λάθος σήμα.", options: { color: TXT } },
    ],
    {
      x: M + 0.3, y: 5.58, w: 11.5, h: 0.7,
      fontFace: BODY, fontSize: 13.5, lineSpacing: 19, margin: 0,
    }
  );

  s.addNotes("Κοινός παρονομαστής: ακρίβεια × επικαιρότητα × overhead — διάλεξε δύο.");
}

// ───────────────────────────────────────────────────────────────────────────
// 6 — Failure mode 2: granularity  (THE central slide)
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Γιατί αποτυγχάνει σήμερα: η κοκκομέτρηση", "ΑΣΤΟΧΙΑ 2 ΑΠΟ 3  ·  ΤΟ ΚΕΝΤΡΙΚΟ ΣΗΜΕΙΟ");

  s.addText(
    "Η πυκνότητα προσπελάσεων μέσα σε μια σελίδα 4 KB είναι εξαιρετικά ανομοιόμορφη. " +
    "Μια αναζήτηση σε hash table αγγίζει 64 bytes από τα 4096.",
    {
      x: M, y: 1.82, w: 12.1, h: 0.55,
      fontFace: BODY, fontSize: 14.5, color: TXT, lineSpacing: 21, margin: 0,
    }
  );

  const cols = [
    {
      x: M, size: "64 B", label: "cache line",
      pro: "Ελάχιστη σπατάλη μεταφοράς",
      con: "Τα μεταδεδομένα εκρήγνυνται·\nο πίνακας σελίδων δεν το χαρτογραφεί",
      col: ICEDK,
    },
    {
      x: 4.63, size: "4 KB", label: "προεπιλογή Linux",
      pro: "Η μονάδα που ξέρει το λειτουργικό",
      con: "Μέτρια και στα δύο:\nσπαταλά και κοστίζει",
      col: AMBER,
    },
    {
      x: 8.66, size: "2 MB", label: "huge page",
      pro: "Φθηνή μετανάστευση ανά byte",
      con: "Τεράστια σπατάλη: 99,99% της\nμεταφοράς μπορεί να είναι ψυχρό",
      col: HOT,
    },
  ];

  cols.forEach((c) => {
    card(s, { x: c.x, y: 2.55, w: 4.04, h: 2.35 });
    s.addText(c.size, {
      x: c.x + 0.25, y: 2.72, w: 3.5, h: 0.55,
      fontFace: HEAD, fontSize: 30, bold: true, color: c.col, margin: 0,
    });
    s.addText(c.label, {
      x: c.x + 0.25, y: 3.28, w: 3.5, h: 0.28,
      fontFace: BODY, fontSize: 11.5, color: MUTED, margin: 0,
    });
    s.addText("+  " + c.pro, {
      x: c.x + 0.25, y: 3.66, w: 3.55, h: 0.42,
      fontFace: BODY, fontSize: 12, color: TXT, lineSpacing: 17, margin: 0,
    });
    s.addText("−  " + c.con, {
      x: c.x + 0.25, y: 4.12, w: 3.55, h: 0.65,
      fontFace: BODY, fontSize: 12, color: MUTED, lineSpacing: 17, margin: 0,
    });
  });

  card(s, { x: M, y: 5.1, w: 12.1, h: 1.35, fill: INK2, line: INK2 });
  s.addText("Δεν υπάρχει PTE για μια cache line.", {
    x: M + 0.4, y: 5.28, w: 11.3, h: 0.38,
    fontFace: BODY, fontSize: 16, bold: true, color: HOT, margin: 0,
  });
  s.addText(
    "Άρα δεν «μεταναστεύεις γραμμές αντί για σελίδες» μέσα από το λειτουργικό. Η λύση είναι είτε " +
    "έμμεση αναφορά σε υλικό (η τοπική DRAM γίνεται κρυφή μνήμη), είτε — και εδώ στοχεύω — " +
    "profiling σε λεπτή κοκκομέτρηση που οδηγεί αποφάσεις σε χονδρή.",
    {
      x: M + 0.4, y: 5.7, w: 11.3, h: 0.62,
      fontFace: BODY, fontSize: 13, color: WHITE, lineSpacing: 18, margin: 0,
    }
  );

  s.addNotes(
    "Αυτό είναι το σημείο που θα με ρωτήσουν. Η απάντηση: κοκκομέτρηση profiling ≠ κοκκομέτρηση migration. " +
    "Το M5 κάνει profiling στα 64 B και migration στα 4 KB — δεν είναι συμβιβασμός, είναι ο σχεδιασμός."
  );
}

// ───────────────────────────────────────────────────────────────────────────
// 7 — Failure mode 3: migration cost
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Γιατί αποτυγχάνει σήμερα: το κόστος μεταφοράς", "ΑΣΤΟΧΙΑ 3 ΑΠΟ 3");

  s.addText("Τι πληρώνει ο πυρήνας για να προάγει μία σελίδα 4 KB:", {
    x: M, y: 1.82, w: 7.4, h: 0.35,
    fontFace: BODY, fontSize: 14.5, color: TXT, margin: 0,
  });

  const costs = [
    ["Αντιγραφή", "4 KB ανάγνωση από CXL + 4 KB εγγραφή σε DDR — καταναλώνει το εύρος ζώνης που θέλεις να σώσεις"],
    ["Ενημέρωση πίνακα σελίδων", "Διάσχιση του rmap για κάθε PTE που χαρτογραφεί τη σελίδα"],
    ["TLB shootdown", "IPI σε κάθε πυρήνα με πιθανή cached μετάφραση — συνήθως το κυρίαρχο κόστος"],
    ["Ανταγωνισμός κλειδωμάτων", "mmap_lock, LRU locks — η μετανάστευση δεν παραλληλοποιείται καλά"],
  ];

  costs.forEach(([h, d], i) => {
    const y = 2.35 + i * 0.94;
    badge(s, i + 1, M, y + 0.02, i === 2 ? HOT : ICEDK, 0.38);
    s.addText(h, {
      x: M + 0.58, y, w: 6.9, h: 0.3,
      fontFace: BODY, fontSize: 14, bold: true,
      color: i === 2 ? HOT : TXT, margin: 0,
    });
    s.addText(d, {
      x: M + 0.58, y: y + 0.31, w: 6.9, h: 0.52,
      fontFace: BODY, fontSize: 12, color: MUTED, lineSpacing: 17, margin: 0,
    });
  });

  card(s, { x: 8.3, y: 2.35, w: 4.4, h: 3.5 });
  s.addText("μsec", {
    x: 8.5, y: 2.82, w: 4.0, h: 0.95,
    fontFace: HEAD, fontSize: 48, bold: true, color: HOT, align: "center", margin: 0,
  });
  s.addText("κόστος ανά μετανάστευση σελίδας", {
    x: 8.5, y: 3.82, w: 4.0, h: 0.32,
    fontFace: BODY, fontSize: 13, bold: true, color: TXT, align: "center", margin: 0,
  });
  s.addText("έναντι των ~250 ns που προσπαθείς να αποφύγεις", {
    x: 8.5, y: 4.18, w: 4.0, h: 0.5,
    fontFace: BODY, fontSize: 12, color: MUTED, align: "center", lineSpacing: 17, margin: 0,
  });
  s.addText(
    "Μια σελίδα πρέπει να ξαναπροσπελαστεί πολλές φορές για να αποσβέσει τη μεταφορά της. " +
    "Γι' αυτό μια λάθος προαγωγή δεν είναι απλώς άχρηστη — είναι ενεργά επιζήμια.",
    {
      x: 8.5, y: 4.82, w: 4.0, h: 0.95,
      fontFace: BODY, fontSize: 12, italic: true, color: TXT, align: "center", lineSpacing: 17, margin: 0,
    }
  );

  s.addNotes("Τάξη μεγέθους: μικροδευτερόλεπτα έναντι νανοδευτερολέπτων. Χιλιαπλάσιο κόστος από αυτό που γλιτώνεις ανά προσπέλαση.");
}

// ───────────────────────────────────────────────────────────────────────────
// 8 — Three papers, three diagnoses
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Τρεις εργασίες, τρεις διαφορετικές διαγνώσεις", "Η ΒΙΒΛΙΟΓΡΑΦΙΑ");

  const rows = [
    [
      { text: "Εργασία", options: { bold: true, color: WHITE, fill: { color: INK }, fontSize: 13 } },
      { text: "Διάγνωση", options: { bold: true, color: WHITE, fill: { color: INK }, fontSize: 13 } },
      { text: "Λύση", options: { bold: true, color: WHITE, fill: { color: INK }, fontSize: 13 } },
      { text: "Κοκκομέτρηση", options: { bold: true, color: WHITE, fill: { color: INK }, fontSize: 13 } },
    ],
    [
      { text: "NeoMem\nMICRO '24", options: { bold: true } },
      "Το profiling είναι αργό και χονδροειδές — διόρθωσέ το και οι σελίδες 4 KB αρκούν",
      "Count-min sketch μέσα στον ελεγκτή CXL + δυναμικό κατώφλι θερμότητας",
      "4 KB",
    ],
    [
      { text: "M5\nASPLOS '25", options: { bold: true, color: HOT } },
      { text: "Η θερμότητα είναι υπο-σελιδική — το πλήθος προσπελάσεων ανά σελίδα παραπλανά", options: { color: HOT } },
      { text: "Top-K trackers για σελίδες (HPT) και για λέξεις 64 B (HWT)", options: { color: HOT } },
      { text: "profiling 64 B\nmigration 4 KB", options: { bold: true, color: HOT } },
    ],
    [
      { text: "Memstrata\nOSDI '24", options: { bold: true } },
      "Το tiering σε υλικό δουλεύει — μέχρι να συνυπάρξουν πολλές VM και να συγκρουστούν",
      "Χρωματισμός σελίδων + online εκτιμητής επιβράδυνσης",
      "64 B (υλικό)",
    ],
  ];

  s.addTable(rows, {
    x: M, y: 1.9, w: 12.1,
    colW: [1.9, 4.1, 4.1, 2.0],
    fontFace: BODY, fontSize: 12.5, color: TXT,
    fill: { color: CARD },
    border: { type: "solid", color: "E3E9F2", pt: 1 },
    valign: "middle",
    margin: [0.06, 0.12, 0.06, 0.12],
  });

  card(s, { x: M, y: 5.15, w: 12.1, h: 1.2, fill: INK2, line: INK2 });
  s.addText(
    [
      { text: "Διαφωνούν μεταξύ τους — και αυτό είναι το ενδιαφέρον. ", options: { bold: true, color: HOT } },
      { text: "Το NeoMem λέει «ανάλυση στον χρόνο», το M5 λέει «ανάλυση στον χώρο», το Memstrata λέει ότι το πρόβλημα εμφανίζεται μόνο υπό συστέγαση φόρτων.", options: { color: WHITE } },
    ],
    {
      x: M + 0.4, y: 5.38, w: 11.3, h: 0.8,
      fontFace: BODY, fontSize: 13.5, lineSpacing: 19, margin: 0,
    }
  );

  s.addNotes("Το ότι διαφωνούν είναι δύναμη στην παρουσίαση: δείχνει ότι διάβασα και τις τρεις, όχι μία.");
}

// ───────────────────────────────────────────────────────────────────────────
// 9 — The honest tradeoff
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Ο έντιμος συμβιβασμός: σελίδες ή γραμμές;", "ΓΙΑΤΙ ΔΕΝ ΕΧΕΙ ΛΥΘΕΙ");

  const attrs = [
    ["Μονάδα", "4 KB / 2 MB", "64 B"],
    ["Ποιος αποφασίζει", "Το OS, με παλιά πληροφορία", "Το υλικό, αντιδραστικά"],
    ["Χαμένη μεταφορά", "Υψηλή", "Σχεδόν μηδενική"],
    ["Σταθερό κόστος ανά κίνηση", "μsec (TLB shootdown)", "nsec"],
    ["Μεταδεδομένα", "Πίνακες σελίδων (ήδη υπάρχουν)", "Πίνακας ετικετών — τεράστιος"],
    ["Χωρητικότητα", "100% αξιοποιήσιμη", "Η γρήγορη βαθμίδα γίνεται cache"],
    ["Αστοχίες σύγκρουσης", "Δεν υφίστανται", "Ναι — και μεταξύ ενοίκων"],
    ["Νέο υλικό", "Όχι", "Ναι"],
  ];

  const hdrY = 1.9;
  card(s, { x: M, y: hdrY, w: 12.1, h: 4.05 });

  s.addText("Μετανάστευση σελίδων (OS)", {
    x: 4.5, y: hdrY + 0.16, w: 3.9, h: 0.32,
    fontFace: BODY, fontSize: 14, bold: true, color: ICEDK, margin: 0,
  });
  s.addText("Caching γραμμών (υλικό)", {
    x: 8.6, y: hdrY + 0.16, w: 3.9, h: 0.32,
    fontFace: BODY, fontSize: 14, bold: true, color: HOT, margin: 0,
  });

  attrs.forEach(([a, b, c], i) => {
    const y = hdrY + 0.62 + i * 0.42;
    s.addText(a, {
      x: M + 0.3, y, w: 3.5, h: 0.36,
      fontFace: BODY, fontSize: 12.5, bold: true, color: TXT, valign: "middle", margin: 0,
    });
    s.addText(b, {
      x: 4.5, y, w: 4.0, h: 0.36,
      fontFace: BODY, fontSize: 12.5, color: MUTED, valign: "middle", margin: 0,
    });
    s.addText(c, {
      x: 8.6, y, w: 4.0, h: 0.36,
      fontFace: BODY, fontSize: 12.5, color: MUTED, valign: "middle", margin: 0,
    });
  });

  s.addText(
    "Η κοκκομέτρηση γραμμής εξαλείφει τη σπατάλη και το σταθερό κόστος — και αγοράζει αστοχίες σύγκρουσης, " +
    "αποθήκευση ετικετών και απώλεια της γρήγορης χωρητικότητας. Δεν είναι καθαρή νίκη.",
    {
      x: M, y: 6.12, w: 12.1, h: 0.6,
      fontFace: BODY, fontSize: 13.5, bold: true, color: TXT, lineSpacing: 19, margin: 0,
    }
  );

  s.addNotes(
    "Αυτή η διαφάνεια ξεχωρίζει το «διάβασα μια εργασία» από το «κατάλαβα το πρόβλημα». Να μην κοπεί."
  );
}

// ───────────────────────────────────────────────────────────────────────────
// 10 — The tool
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Το εργαλείο: CXLRAMSim", "ΜΕΘΟΔΟΛΟΓΙΑ");

  s.addText(
    "Πλήρης προσομοίωση συστήματος πάνω σε gem5 v25, με εκκίνηση Linux 6.14. " +
    "Μοντελοποιεί τη συσκευή CXL στη σωστή θέση πάνω στον δίαυλο I/O — άρα ο πυρήνας, " +
    "οι οδηγοί και η στοίβα λογισμικού μένουν αναλλοίωτοι.",
    {
      x: M, y: 1.82, w: 12.1, h: 0.75,
      fontFace: BODY, fontSize: 14.5, color: TXT, lineSpacing: 21, margin: 0,
    }
  );

  const comps = [
    ["Firmware", "Πίνακες ACPI: MCFG, DSDT,\nCEDT, SRAT για ανακάλυψη"],
    ["CXL.io", "Root Complex και σύνολα\nκαταχωρητών για απαρίθμηση"],
    ["CXL.mem", "Επίπεδο συναλλαγών,\nκανάλια M2S / S2M"],
    ["Συνοχή", "MESI δύο επιπέδων,\nκατανεμημένος κατάλογος"],
  ];
  comps.forEach(([h, d], i) => {
    const x = M + i * 3.08;
    card(s, { x, y: 2.75, w: 2.86, h: 1.5 });
    s.addText(h, {
      x: x + 0.22, y: 2.92, w: 2.5, h: 0.32,
      fontFace: BODY, fontSize: 14, bold: true, color: ICEDK, margin: 0,
    });
    s.addText(d, {
      x: x + 0.22, y: 3.28, w: 2.5, h: 0.85,
      fontFace: BODY, fontSize: 11.5, color: MUTED, lineSpacing: 16, margin: 0,
    });
  });

  card(s, { x: M, y: 4.5, w: 12.1, h: 1.85, fill: INK2, line: INK2 });
  s.addText("Πού μπαίνει ο δικός μου κώδικας", {
    x: M + 0.4, y: 4.68, w: 11.3, h: 0.32,
    fontFace: BODY, fontSize: 14, bold: true, color: HOT, margin: 0,
  });
  s.addText(
    "Στο σημείο όπου ο κόμβος CXL απο-πακετοποιεί ένα αίτημα M2S σε προσπέλαση DRAM, " +
    "έχω {φυσική διεύθυνση, ανάγνωση/εγγραφή, χρονική στιγμή}.",
    {
      x: M + 0.4, y: 5.06, w: 11.3, h: 0.5,
      fontFace: BODY, fontSize: 13, color: WHITE, lineSpacing: 18, margin: 0,
    }
  );
  s.addText(
    "Αυτό είναι ακριβώς η ροή αστοχιών LLC προς το CXL που κάνουν profiling το NeoMem και το M5 — " +
    "δεν μπορείς να δεις τίποτε άλλο από εκεί. Ο profiler είναι μια λήψη πάνω σε αυτό το μονοπάτι.",
    {
      x: M + 0.4, y: 5.6, w: 11.3, h: 0.55,
      fontFace: BODY, fontSize: 13, color: ICE, lineSpacing: 18, margin: 0,
    }
  );

  s.addNotes(
    "Ανοιχτό θέμα: χρειάζομαι πρόσβαση στο αποθετήριο του CXLRAMSim. Η δημοσίευση λέει ότι σχεδιάζουν " +
    "να το ανοίξουν, αλλά δεν βρήκα δημόσιο repo."
  );
}

// ───────────────────────────────────────────────────────────────────────────
// 11 — The experiment
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Το πείραμα που αποδεικνύει το πρόβλημα", "ΣΧΕΔΙΟ ΑΞΙΟΛΟΓΗΣΗΣ");

  s.addText("Πέντε σκέλη σύγκρισης", {
    x: M, y: 1.8, w: 5.4, h: 0.3,
    fontFace: BODY, fontSize: 14, bold: true, color: TXT, margin: 0,
  });

  const arms = [
    ["Όλα σε CXL", "κάτω φράγμα", MUTED],
    ["Όλα σε τοπική DRAM", "άνω φράγμα", MUTED],
    ["Αφελής μετανάστευση σελίδων", "το «πρόβλημα»", HOT],
    ["Σχήμα του M5 (HPT + HWT)", "η πρόταση", ICEDK],
    ["Oracle τοποθέτηση", "βέλτιστο offline", MUTED],
  ];
  arms.forEach(([a, tag, col], i) => {
    const y = 2.22 + i * 0.55;
    s.addShape(pres.ShapeType.roundRect, {
      x: M, y, w: 5.4, h: 0.44,
      fill: { color: CARD }, rectRadius: 0.04,
      line: { color: col === MUTED ? "E3E9F2" : col, width: col === MUTED ? 1 : 1.5 },
    });
    s.addText(a, {
      x: M + 0.2, y, w: 3.3, h: 0.44,
      fontFace: BODY, fontSize: 12.5, bold: col !== MUTED, color: TXT, valign: "middle", margin: 0,
    });
    s.addText(tag, {
      x: M + 3.6, y, w: 1.65, h: 0.44,
      fontFace: BODY, fontSize: 11, italic: true, color: col, align: "right", valign: "middle", margin: 0,
    });
  });

  s.addText(
    "Η απόσταση ανάμεσα στο αφελές σκέλος και στο oracle είναι το πρόβλημα που αναπαράγω.",
    {
      x: M, y: 5.1, w: 5.4, h: 0.6,
      fontFace: BODY, fontSize: 12.5, bold: true, color: HOT, lineSpacing: 18, margin: 0,
    }
  );

  s.addText("Φόρτοι εργασίας", {
    x: 6.5, y: 1.8, w: 6.2, h: 0.3,
    fontFace: BODY, fontSize: 14, bold: true, color: TXT, margin: 0,
  });
  s.addText(
    [
      { text: "GUPS — τυχαίες ενημερώσεις 8 B, μηδενική χωρική τοπικότητα· η αντίπαλη περίπτωση", options: { bullet: true, breakLine: true } },
      { text: "XSBench — αναζητήσεις Monte Carlo σε μεγάλους πίνακες", options: { bullet: true, breakLine: true } },
      { text: "PageRank — άτακτη προσπέλαση γράφου, μετακινούμενο θερμό σύνολο", options: { bullet: true, breakLine: true } },
      { text: "Btree / YCSB-C — λοξή κατανομή Zipf, ακραία υπο-σελιδική θερμότητα", options: { bullet: true } },
    ],
    {
      x: 6.5, y: 2.22, w: 6.2, h: 1.65,
      fontFace: BODY, fontSize: 12.5, color: TXT, lineSpacing: 18, paraSpaceAfter: 6, margin: 0,
    }
  );

  s.addText("Μετρικές", {
    x: 6.5, y: 4.05, w: 6.2, h: 0.3,
    fontFace: BODY, fontSize: 14, bold: true, color: TXT, margin: 0,
  });
  s.addText(
    [
      { text: "Αθροιστική κατανομή πυκνότητας προσπελάσεων ανά γραμμή 64 B", options: { bullet: true, breakLine: true } },
      { text: "Απόδοση μεταφοράς: bytes που μεταφέρθηκαν ÷ bytes που όντως χρησιμοποιήθηκαν", options: { bullet: true, breakLine: true } },
      { text: "Επικαιρότητα προαγωγής και ποσοστό σελίδων ακόμη θερμών κατά την προαγωγή", options: { bullet: true, breakLine: true } },
      { text: "Επιβράδυνση συναρτήσει του λόγου γρήγορης βαθμίδας· πλήθος ping-pong", options: { bullet: true } },
    ],
    {
      x: 6.5, y: 4.47, w: 6.2, h: 1.7,
      fontFace: BODY, fontSize: 12.5, color: TXT, lineSpacing: 18, paraSpaceAfter: 6, margin: 0,
    }
  );

  s.addNotes("Πάντα αναφέρω και τα δύο φράγματα δίπλα σε κάθε σχήμα — αλλιώς το νούμερο δεν ερμηνεύεται.");
}

// ───────────────────────────────────────────────────────────────────────────
// 12 — The figure (native chart, hypothetical)
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Η εικόνα στην οποία κρίνεται η εργασία", "ΤΟ ΖΗΤΟΥΜΕΝΟ ΑΠΟΤΕΛΕΣΜΑ");

  s.addText(
    "Για κάθε σελίδα 4 KB: τι ποσοστό των προσπελάσεών της συγκεντρώνεται στις k θερμότερες " +
    "γραμμές των 64 B; Αν το 80% των προσπελάσεων πέφτει σε λιγότερο από το 10% της σελίδας, " +
    "το επιχείρημα της κοκκομέτρησης αποδεικνύεται σε ένα διάγραμμα.",
    {
      x: M, y: 1.8, w: 5.3, h: 1.35,
      fontFace: BODY, fontSize: 13.5, color: TXT, lineSpacing: 20, margin: 0,
    }
  );

  card(s, { x: M, y: 3.35, w: 5.3, h: 1.5, fill: "FDF0EF", line: "F6C9C7" });
  s.addText("Προσοχή στην ανάγνωση", {
    x: M + 0.3, y: 3.52, w: 4.7, h: 0.3,
    fontFace: BODY, fontSize: 12.5, bold: true, color: HOT, margin: 0,
  });
  s.addText(
    "Η καμπύλη δίπλα είναι η αναμενόμενη μορφή, όχι μετρημένα δεδομένα. " +
    "Δεν έχω τρέξει ακόμα τον προσομοιωτή.",
    {
      x: M + 0.3, y: 3.86, w: 4.7, h: 0.8,
      fontFace: BODY, fontSize: 12.5, color: TXT, lineSpacing: 18, margin: 0,
    }
  );

  s.addText(
    "Αν η καμπύλη βγει επίπεδη, το επιχείρημα της υπο-σελιδικής θερμότητας καταρρέει " +
    "για αυτόν τον φόρτο — και αυτό είναι εξίσου χρήσιμο αποτέλεσμα.",
    {
      x: M, y: 5.1, w: 5.3, h: 0.85,
      fontFace: BODY, fontSize: 12.5, italic: true, color: MUTED, lineSpacing: 18, margin: 0,
    }
  );

  const cats = ["1", "4", "8", "16", "24", "32", "48", "64"];
  s.addChart(
    pres.ChartType.line,
    [
      { name: "Zipf (Btree / YCSB)", labels: cats, values: [31, 62, 78, 88, 93, 96, 99, 100] },
      { name: "Ομοιόμορφη (GUPS)", labels: cats, values: [2, 6, 13, 25, 38, 50, 75, 100] },
    ],
    {
      x: 6.35, y: 1.85, w: 6.35, h: 4.4,
      showTitle: true,
      title: "Αθροιστικό % προσπελάσεων στις k θερμότερες γραμμές 64 B",
      titleFontSize: 12, titleColor: TXT, titleFontFace: BODY,
      chartColors: [HOT, ICEDK],
      lineSize: 3, lineSmooth: true,
      showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: TXT,
      catAxisTitle: "k θερμότερες γραμμές των 64 B μέσα στη σελίδα (από 64)",
      showCatAxisTitle: true, catAxisTitleFontSize: 10, catAxisTitleColor: MUTED,
      valAxisTitle: "Αθροιστικό % προσπελάσεων",
      showValAxisTitle: true, valAxisTitleFontSize: 10, valAxisTitleColor: MUTED,
      catAxisLabelColor: MUTED, valAxisLabelColor: MUTED,
      catAxisLabelFontSize: 10, valAxisLabelFontSize: 10,
      valAxisMaxVal: 100, valAxisMinVal: 0,
      valGridLine: { color: "E3E9F2", size: 1 },
      catGridLine: { style: "none" },
    }
  );

  s.addNotes(
    "Σκίτσο, όχι δεδομένα — και το δηλώνω. Ο Zipf φόρτος δείχνει ακραία συγκέντρωση· το GUPS είναι " +
    "σχεδόν ομοιόμορφο και λειτουργεί ως αρνητικός έλεγχος."
  );
}

// ───────────────────────────────────────────────────────────────────────────
// 13 — Timeline
// ───────────────────────────────────────────────────────────────────────────
{
  const s = lightSlide();
  title(s, "Φάσεις και διαχείριση ρίσκου", "ΧΡΟΝΟΔΙΑΓΡΑΜΜΑ");

  const phases = [
    ["Φ1", "Εκκίνηση και checkpoint", "Boot σε shell, επιβεβαίωση κόμβου zNUMA, microbenchmark καθυστέρησης: «απόδειξε ότι το CXL είναι αργό»"],
    ["Φ2", "Λήψη ιχνών προσπέλασης", "Σημείο λήψης στη ροή αιτημάτων της συσκευής· κατανομή πυκνότητας — πρώτο πραγματικό αποτέλεσμα"],
    ["Φ3", "Βασική γραμμή μεταφοράς", "Αφελής μετανάστευση σελίδων με έντιμο μοντέλο κόστους και ποσόστωση εύρους ζώνης"],
    ["Φ4", "Υλοποίηση M5", "Πρώτα το HPT, μετά το HWT ως το διαφοροποιητικό στοιχείο"],
    ["Φ5", "Αξιολόγηση και συγγραφή", "Ευαισθησία σε K, διάστημα, ποσόστωση, καθυστέρηση CXL"],
  ];

  phases.forEach(([p, h, d], i) => {
    const y = 1.9 + i * 0.92;
    const accent = i === 1 ? HOT : ICEDK;
    card(s, { x: M, y, w: 12.1, h: 0.8 });
    s.addShape(pres.ShapeType.ellipse, { x: M + 0.28, y: y + 0.19, w: 0.42, h: 0.42, fill: { color: accent } });
    s.addText(p, {
      x: M + 0.28, y: y + 0.19, w: 0.42, h: 0.42,
      fontFace: BODY, fontSize: 12, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0,
    });
    s.addText(h, {
      x: M + 0.88, y: y + 0.08, w: 3.1, h: 0.64,
      fontFace: BODY, fontSize: 13.5, bold: true, color: TXT, valign: "middle", margin: 0,
    });
    s.addText(d, {
      x: M + 4.05, y: y + 0.08, w: 7.85, h: 0.64,
      fontFace: BODY, fontSize: 11.5, color: MUTED, valign: "middle", lineSpacing: 16, margin: 0,
    });
  });

  s.addText(
    "Η Φ2 απομειώνει το ρίσκο όλων των υπολοίπων: παράγει παρουσιάσιμο αποτέλεσμα πριν γραφτεί " +
    "οποιαδήποτε πολιτική. Προαιρετικές επεκτάσεις: μοντέλο κόστους υλικού, σάρωση καθυστέρησης, δύο ταυτόχρονοι φόρτοι.",
    {
      x: M, y: 6.55, w: 12.1, h: 0.6,
      fontFace: BODY, fontSize: 12, italic: true, color: MUTED, lineSpacing: 17, margin: 0,
    }
  );

  s.addNotes("Δηλώνω ξεκάθαρα τι είναι βασικό και τι είναι stretch goal.");
}

// ───────────────────────────────────────────────────────────────────────────
// 14 — Open questions
// ───────────────────────────────────────────────────────────────────────────
{
  const s = darkSlide();

  s.addText("ΠΡΟΣ ΣΥΖΗΤΗΣΗ", {
    x: M, y: 0.75, w: 8, h: 0.3,
    fontFace: BODY, fontSize: 13, bold: true, color: HOT, charSpacing: 2.2, margin: 0,
  });
  s.addText("Ανοιχτά ερωτήματα προς εσάς", {
    x: M, y: 1.1, w: 11, h: 0.7,
    fontFace: HEAD, fontSize: 34, bold: true, color: WHITE, margin: 0,
  });

  const qs = [
    ["Πρόσβαση στο CXLRAMSim", "Υπάρχει αποθετήριο και οδηγίες build; Ιδανικά και έτοιμο disk image — το χτίσιμο από το μηδέν είναι παράκαμψη ημερών."],
    ["Κλίμακα φόρτων", "Είναι αποδεκτό να κατεβάσω το μέγεθος σε εκατοντάδες MB αντί για 10–20 GB RSS, κρατώντας ρεαλιστικό τον λόγο των βαθμίδων;"],
    ["Εύρος υλοποίησης", "Αρκεί profiler HPT+HWT με μοντελοποιημένη μηχανή μεταφοράς, ή θέλετε πραγματική μετανάστευση Linux από kernel module;"],
    ["Επιλογή εργασίας", "Είναι το M5 η σωστή επιλογή, ή προτιμάτε να δείτε NeoMem;"],
  ];

  qs.forEach(([h, d], i) => {
    const y = 2.15 + i * 1.12;
    s.addShape(pres.ShapeType.roundRect, {
      x: M, y, w: 12.1, h: 0.95,
      fill: { color: INK2 }, rectRadius: 0.05, line: { color: "2A3654", width: 1 },
    });
    badge(s, i + 1, M + 0.32, y + 0.26, HOT, 0.42);
    s.addText(h, {
      x: M + 0.95, y: y + 0.13, w: 3.4, h: 0.32,
      fontFace: BODY, fontSize: 13.5, bold: true, color: HOT, margin: 0,
    });
    s.addText(d, {
      x: M + 0.95, y: y + 0.45, w: 10.9, h: 0.42,
      fontFace: BODY, fontSize: 12, color: ICE, lineSpacing: 16, margin: 0,
    });
  });

  s.addText("github.com/Zajason/memory_tiering", {
    x: M, y: 6.75, w: 12.1, h: 0.3,
    fontFace: BODY, fontSize: 11.5, color: MUTED, margin: 0,
  });

  s.addNotes(
    "Το να ρωτάω ανοιχτά είναι δύναμη, όχι αδυναμία. Και έχω έτοιμη την απάντηση για το «γιατί όχι " +
    "απευθείας cache lines»: δεν υπάρχει PTE για γραμμή → χρειάζεται έμμεση αναφορά σε υλικό → " +
    "αυτό είναι το Flat Memory Mode → που κοστίζει αστοχίες σύγκρουσης και χωρητικότητα → " +
    "που είναι ακριβώς αυτό που έρχεται να λύσει το Memstrata."
  );
}

const out = path.join(__dirname, "..", "docs", "memory-tiering-cxl-gr.pptx");
pres.writeFile({ fileName: out }).then(() => console.log("wrote " + out));
