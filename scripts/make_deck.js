// Generates docs/memory-tiering-cxl-gr.pptx — concept presentation (Greek)
// Content follows docs/presentation-outline.md
//
// Visual paradigm: an academic conference talk (LaTeX/Beamer). Serif type
// throughout (Times New Roman), white background, numbered sections (§3.2) and
// captioned figures/tables (Σχήμα N, Πίνακας N) in booktabs style, dense prose
// instead of bullet fragments, a thin footline, and only two restrained colors
// used the way Beamer uses \structure{} (navy) and \alert{} (dark red).
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
const NAVY = "1F3A63"; // \structure — section numbers, headings, primary rule
const ALERT = "8C2A2A"; // \alert — sparing emphasis
const RULE = "BFBFBF"; // hairlines
const BLK = "F0F0EE"; // block body fill (Beamer block)
const BLKA = "F7ECEC"; // alert-block body fill

const SERIF = "Times New Roman";
const CODE = "Courier New";

const ML = 0.85; // content left
const MR = 12.48; // content right
const CW = MR - ML; // 11.63
const FOOT = "Memory Tiering σε συστήματα CXL  ·  el23408";

// ── Helpers ──────────────────────────────────────────────────────────────────
// A frame: white slide with a §-numbered frametitle and a Beamer-style footline.
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
  // footline
  s.addShape(pres.ShapeType.rect, { x: ML, y: 7.04, w: CW, h: 0.008, fill: { color: RULE } });
  s.addText(FOOT, { x: ML, y: 7.1, w: 6.5, h: 0.3, fontFace: SERIF, fontSize: 9.5, color: MUT, margin: 0, valign: "middle" });
  s.addText(secName, { x: ML + 6.5, y: 7.1, w: 3.5, h: 0.3, fontFace: SERIF, fontSize: 9.5, italic: true, color: MUT, align: "center", margin: 0, valign: "middle" });
  s.addText(`${n} / 14`, { x: MR - 1.5, y: 7.1, w: 1.5, h: 0.3, fontFace: SERIF, fontSize: 9.5, color: MUT, align: "right", margin: 0, valign: "middle" });
  return s;
}

// Booktabs table: no cell borders/fills; thick top & bottom rules, thin rule
// under the (bold) header row. The academic table look.
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
  s.addShape(pres.ShapeType.rect, { x, y, w, h: 0.022, fill: { color: INK } });          // top rule
  s.addShape(pres.ShapeType.rect, { x, y: y + h0, w, h: 0.01, fill: { color: RULE } });   // header sep
  s.addShape(pres.ShapeType.rect, { x, y: y + tot, w, h: 0.022, fill: { color: INK } });  // bottom rule
}
// bold header cell
const hb = (t) => ({ text: t, options: { bold: true } });

// Caption line (Σχήμα N: ... / Πίνακας N: ...)
function caption(s, x, y, w, label, text, align = "left") {
  s.addText(
    [
      { text: label + " ", options: { bold: true } },
      { text: text, options: {} },
    ],
    { x, y, w, h: 0.32, fontFace: SERIF, fontSize: 11, italic: true, color: MUT, align, margin: 0 }
  );
}

// Beamer block: titled box, subtle fill, sharp corners, no shadow.
function block(s, x, y, w, h, title, body, alert) {
  s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color: alert ? BLKA : BLK } });
  s.addText(title, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.32, fontFace: SERIF, fontSize: 14.5, bold: true, color: alert ? ALERT : NAVY, margin: 0 });
  s.addText(body, { x: x + 0.2, y: y + 0.48, w: w - 0.4, h: h - 0.6, fontFace: SERIF, fontSize: 13.5, color: INK, lineSpacing: 19, margin: 0, valign: "top" });
}

// ═════════════════════════════════════════════════════════════════════════════
// 01 — Title page (like a paper front page)
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
    "Προσομοίωση τεχνικών ιεραρχικής διαχείρισης μνήμης με υποστήριξη υλικού, στον προσομοιωτή CXLRAMSim",
    { x: ML, y: 2.35, w: CW, h: 0.72, fontFace: SERIF, fontSize: 18, italic: true, color: NAVY, lineSpacing: 24, margin: 0 }
  );

  s.addShape(pres.ShapeType.rect, { x: ML, y: 3.18, w: CW, h: 0.014, fill: { color: RULE } });

  // Abstract, as in a paper
  s.addText("Περίληψη.", { x: ML, y: 3.35, w: 2.0, h: 0.3, fontFace: SERIF, fontSize: 14, bold: true, color: INK, margin: 0 });
  s.addText(
    "Οι μνήμες CXL προσφέρουν φθηνή χωρητικότητα πάνω από τον δίαυλο PCIe, με το τίμημα ~2–3× " +
    "μεγαλύτερης καθυστέρησης· σχηματίζουν έτσι ένα σύστημα μνήμης δύο βαθμίδων. Η παρούσα εργασία " +
    "αναπαράγει, στον προσομοιωτή CXLRAMSim, γιατί η μετανάστευση σελίδων 4 KB από το λειτουργικό " +
    "σύστημα αποτυγχάνει να γεφυρώσει το χάσμα επίδοσης προς την τοπική DRAM, και εξετάζει λύσεις " +
    "με υποστήριξη υλικού (M5, NeoMem, Memstrata) που κάνουν profiling μέσα στη συσκευή CXL.",
    { x: ML + 0.35, y: 3.68, w: CW - 0.35, h: 1.5, fontFace: SERIF, fontSize: 14.5, color: INK, lineSpacing: 21, align: "justify", margin: 0 }
  );
  s.addText(
    [
      { text: "Λέξεις-κλειδιά:  ", options: { bold: true } },
      { text: "CXL · memory tiering · μετανάστευση σελίδων · profiling υλικού · κοκκομέτρηση", options: { italic: true } },
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

  s.addNotes("Στόχος: δείχνω ότι κατάλαβα το πρόβλημα και ότι έχω αξιόπιστο πλάνο. Δεν έχω ακόμα αποτελέσματα — και το λέω ανοιχτά.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 02 — Motivation
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(2, "§1.1", "1. Κίνητρο", "Η μνήμη είναι ο περιοριστικός πόρος");

  s.addText(
    "Η χωρητικότητα της μνήμης ανά επεξεργαστικό socket έχει φτάσει σε τοίχο: περιορισμένος αριθμός " +
    "από DIMM slots και pins DDR. Για να αποκτήσει κανείς περισσότερη μνήμη αναγκάζεται να αγοράσει " +
    "περισσότερους επεξεργαστές τους οποίους δεν χρειάζεται. Το CXL σπάει αυτόν τον δεσμό, επιτρέποντας " +
    "επέκταση της χωρητικότητας πάνω από τον δίαυλο PCIe, ανεξάρτητα από τους πυρήνες.",
    { x: ML, y: 1.45, w: CW, h: 1.35, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );

  block(
    s, ML, 3.0, CW, 1.35, "Παρατήρηση 1 — αποκομμένη («stranded») μνήμη",
    "Σε στόλους cloud υπερκλίμακας, περίπου το 25% της εγκατεστημένης DRAM παραμένει αναξιοποίητο, " +
    "επειδή οι πυρήνες του μηχανήματος έχουν ήδη διατεθεί σε άλλους ενοίκους. Το CXL στοχεύει ακριβώς " +
    "στην ανάκτηση αυτής της αποκομμένης χωρητικότητας (Azure — Pond, ASPLOS ’23)."
  );

  s.addText(
    "Αυτό το οικονομικό κίνητρο —φθηνή, κοινόχρηστη χωρητικότητα— είναι που κάνει το CXL ελκυστικό. " +
    "Το τεχνικό τίμημα, όμως, είναι η καθυστέρηση προσπέλασης, την οποία εξετάζουμε στη συνέχεια.",
    { x: ML, y: 4.65, w: CW, h: 0.9, fontFace: SERIF, fontSize: 15, italic: true, color: MUT, lineSpacing: 22, align: "justify", margin: 0 }
  );

  s.addNotes("Ένας αριθμός να μείνει: ~25% stranded DRAM. Το οικονομικό κίνητρο όλου του πεδίου.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 03 — What CXL costs
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(3, "§1.2", "1. Κίνητρο", "Το τίμημα: η καθυστέρηση της CXL");

  caption(s, ML, 1.4, 6.7, "Πίνακας 1:", "τυπικές τιμές καθυστέρησης και εύρους ζώνης ανά διαδρομή.");
  booktabs(s, ML, 1.75, [2.9, 2.0, 1.8], [
    [hb("Διαδρομή"), hb("Καθυστέρηση"), hb("Εύρος ζώνης")],
    ["Τοπική DDR5", { text: "80–100 ns", options: { fontFace: CODE, fontSize: 12 } }, "30–50 GB/s"],
    ["Απομακρ. NUMA socket", { text: "140–180 ns", options: { fontFace: CODE, fontSize: 12 } }, "—"],
    [
      { text: "Μνήμη CXL (x8 Gen5)", options: { bold: true } },
      { text: "250–400 ns", options: { fontFace: CODE, fontSize: 12, bold: true, color: ALERT } },
      { text: "25–30 GB/s", options: { bold: true } },
    ],
  ], [0.42, 0.42, 0.42, 0.42]);

  s.addText(
    [
      { text: "Η καθυστέρηση είναι ", options: {} },
      { text: "2–3× μεγαλύτερη", options: { bold: true, color: ALERT } },
      { text: " από την τοπική DDR — παρότι η DRAM πάνω στην κάρτα είναι κοινή DDR5. Το τίμημα το πληρώνει η ", options: {} },
      { text: "διασύνδεση", options: { italic: true } },
      { text: ", όχι η μνήμη. Συνεπώς φόρτοι δεσμευμένοι από καθυστέρηση (pointer chasing) υποφέρουν, ενώ φόρτοι δεσμευμένοι από εύρος ζώνης σχεδόν δεν το αντιλαμβάνονται.", options: {} },
    ],
    { x: ML, y: 3.9, w: 6.7, h: 1.7, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 23, align: "justify", margin: 0 }
  );

  // Σχήμα 1: request path as a typeset enumeration
  const fx = 8.15, fw = CW - (fx - ML);
  s.addText("Η διαδρομή ενός load που αστοχεί στην LLC:", {
    x: fx, y: 1.4, w: fw, h: 0.32, fontFace: SERIF, fontSize: 13.5, italic: true, color: INK, margin: 0,
  });
  const steps = [
    "Πυρήνας CPU  →  αστοχία LLC", "CXL Root Complex", "πακετοποίηση M2S", "σύνδεσμος PCIe (SERDES)",
    "ελεγκτής συσκευής  →  de-packetize", "DRAM στην κάρτα", "και όλη η διαδρομή αντίστροφα (S2M)",
  ];
  steps.forEach((t, i) => {
    const y = 1.85 + i * 0.42;
    s.addText(`(${i + 1})`, { x: fx, y, w: 0.5, h: 0.32, fontFace: CODE, fontSize: 12, color: NAVY, margin: 0, valign: "middle" });
    s.addText(t, { x: fx + 0.55, y, w: fw - 0.55, h: 0.32, fontFace: SERIF, fontSize: 14, color: i === 6 ? MUT : INK, italic: i === 6, margin: 0, valign: "middle" });
  });
  caption(s, fx, 4.98, fw, "Σχήμα 1:", "κάθε στάδιο προσθέτει καθυστέρηση· η διασύνδεση κυριαρχεί.");

  s.addNotes("Το σημείο: η DRAM στην κάρτα είναι κανονική DDR5. Η διασύνδεση είναι ο φόρος — γι' αυτό υπάρχει tiering.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 04 — The tiering problem stated
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(4, "§2", "2. Το πρόβλημα", "Το πρόβλημα του tiering");

  s.addText(
    "Έχουμε δύο βαθμίδες μνήμης — μια γρήγορη και μικρή (τοπική DDR) και μια αργή και μεγάλη (CXL). " +
    "Σκοπός είναι να διατηρούνται τα «θερμά» δεδομένα στη γρήγορη βαθμίδα. Αν επιτευχθεί, ένα μηχάνημα " +
    "με μόλις 25% τοπική DRAM αποδίδει σχεδόν σαν να διέθετε 100%.",
    { x: ML, y: 1.45, w: CW, h: 0.95, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );

  const bw = (CW - 0.4) / 2;
  block(s, ML, 2.55, bw, 1.55, "Ορισμός — Προαγωγή (promotion)",
    "Μετακίνηση σελίδας από την αργή στη γρήγορη βαθμίδα. Πρέπει να είναι έγκαιρη: μια σελίδα που " +
    "προάγεται αφού έχει ήδη κρυώσει αποτελεί καθαρή σπατάλη.");
  block(s, ML + bw + 0.4, 2.55, bw, 1.55, "Ορισμός — Υποβάθμιση (demotion)",
    "Μετακίνηση σελίδας από τη γρήγορη στην αργή βαθμίδα. Πρέπει να είναι ασφαλής: η υποβάθμιση " +
    "μιας ακόμη θερμής σελίδας προκαλεί ταλάντωση (ping-pong).");

  s.addText(
    [
      { text: "Η υποβάθμιση είναι το εύκολο μέρος — μια προσέγγιση LRU αρκεί, και ο πυρήνας του Linux ήδη διαθέτει LRU. ", options: {} },
      { text: "Η προαγωγή είναι το ανοιχτό πρόβλημα:", options: { bold: true, color: ALERT } },
      { text: " απαιτεί να γνωρίζουμε ότι μια σελίδα είναι θερμή τη δεδομένη στιγμή, και αυτό κοστίζει. Είναι θέση που διατυπώνει ρητά και η ίδια η κοινότητα του Linux MM.", options: {} },
    ],
    { x: ML, y: 4.4, w: CW, h: 1.4, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );

  s.addNotes("Γιατί δύσκολη η προαγωγή: απαιτεί να ξέρεις ότι μια σελίδα είναι θερμή ΤΩΡΑ.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 05 — Failure mode 1: profiling
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(5, "§3.1", "3. Γιατί αποτυγχάνει", "Αστοχία: το profiling");

  caption(s, ML, 1.4, CW, "Πίνακας 2:", "μηχανισμοί εντοπισμού θερμών σελίδων και το θεμελιώδες ελάττωμα καθενός.");
  booktabs(s, ML, 1.75, [2.6, 4.0, 5.03], [
    [hb("Μηχανισμός"), hb("Αρχή λειτουργίας"), hb("Θεμελιώδες ελάττωμα")],
    [
      { text: "PTE-scan (DAMON)", options: { fontFace: CODE, fontSize: 11.5 } },
      "Σάρωση των access bits των PTE",
      "1 bit = δυαδική πληροφορία· η σάρωση διαρκεί δευτερόλεπτα — το θερμό σύνολο έχει ήδη αλλάξει",
    ],
    [
      { text: "hint faults (AutoNUMA, TPP)", options: { fontFace: CODE, fontSize: 11 } },
      "Σκόπιμη απο-χαρτογράφηση PTE ώστε η προσπέλαση να παγιδεύεται",
      { text: "Μετρά αστοχίες TLB, όχι αστοχίες LLC — συσχετίζονται ασθενώς", options: { color: ALERT } },
    ],
    [
      { text: "PEBS / IBS (Memtis)", options: { fontFace: CODE, fontSize: 11.5 } },
      "Δειγματοληψία της PMU σε αστοχίες LLC",
      "Το overhead ακολουθεί τον ρυθμό δειγματοληψίας: >50% επιβράδυνση σε πυκνά δείγματα",
    ],
    [
      { text: "υλικό στη συσκευή CXL", options: { fontFace: CODE, fontSize: 11.5, color: NAVY, bold: true } },
      { text: "Μετρητές μέσα στον ελεγκτή της συσκευής", options: { color: NAVY } },
      { text: "Σωστό γεγονός, μηδενικό κόστος CPU — αλλά απαιτεί νέο υλικό", options: { color: NAVY, bold: true } },
    ],
  ], [0.42, 0.7, 0.7, 0.7, 0.62]);

  s.addText(
    [
      { text: "Το κρίσιμο σημείο. ", options: { bold: true, color: ALERT } },
      { text: "Οι AutoNUMA και TPP μετρούν αστοχίες TLB, αλλά την κίνηση προς τη μνήμη CXL την καθορίζουν οι αστοχίες LLC· μια σελίδα μπορεί να είναι έντονα θερμή ως προς το TLB και σχεδόν αόρατη ως προς την κίνηση CXL. Βελτιστοποιούν, δηλαδή, το λάθος σήμα.", options: {} },
    ],
    { x: ML, y: 5.55, w: CW, h: 1.1, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 22, align: "justify", margin: 0 }
  );

  s.addNotes("Κοινός παρονομαστής: ακρίβεια × επικαιρότητα × overhead — διάλεξε δύο.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 06 — Failure mode 2: granularity (central)
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(6, "§3.2", "3. Γιατί αποτυγχάνει", "Αστοχία: η κοκκομέτρηση");

  s.addText(
    "Η πυκνότητα των προσπελάσεων μέσα σε μια σελίδα 4 KB είναι εξαιρετικά ανομοιόμορφη: μια αναζήτηση " +
    "σε πίνακα κατακερματισμού αγγίζει 64 bytes από τα 4096 (βλ. Σχήμα 2). Το 4 KB είναι λάθος μονάδα " +
    "και προς τις δύο κατευθύνσεις — υπερβολικά χονδρό για ό,τι είναι πραγματικά θερμό, αλλά και " +
    "υπερβολικά λεπτό για τον μηχανισμό μετανάστευσης, που πληρώνει σταθερό κόστος ανά σελίδα.",
    { x: ML, y: 1.42, w: CW, h: 1.35, fontFace: SERIF, fontSize: 15.5, color: INK, lineSpacing: 23, align: "justify", margin: 0 }
  );

  // Σχήμα 2: the scale spectrum, typeset restrained (no big color blocks)
  const cols = [["64 B", "cache line", "ελάχιστη σπατάλη· μη διαχειρίσιμα μεταδεδομένα"],
                ["4 KB", "προεπιλογή Linux", "μέτριο και στα δύο: σπαταλά και κοστίζει"],
                ["2 MB", "huge page", "φθηνή μετανάστευση· τεράστια σπατάλη (>99%)"]];
  const spanW = CW, cwv = (spanW - 1.0) / 3;
  cols.forEach((c, i) => {
    const x = ML + i * (cwv + 0.5);
    s.addText(c[0], { x, y: 2.95, w: cwv, h: 0.5, fontFace: SERIF, fontSize: 28, bold: true, color: NAVY, align: "center", margin: 0 });
    s.addText(c[1], { x, y: 3.5, w: cwv, h: 0.28, fontFace: CODE, fontSize: 11, color: MUT, align: "center", margin: 0 });
    s.addText(c[2], { x, y: 3.82, w: cwv, h: 0.6, fontFace: SERIF, fontSize: 12.5, italic: true, color: INK, align: "center", lineSpacing: 16, margin: 0 });
    if (i < 2) s.addText("−→", { x: x + cwv, y: 2.95, w: 0.5, h: 0.5, fontFace: SERIF, fontSize: 20, color: MUT, align: "center", valign: "middle", margin: 0 });
  });
  caption(s, ML, 4.5, CW, "Σχήμα 2:", "το φάσμα κοκκομέτρησης — καμία επιλογή δεν είναι καλή ταυτόχρονα σε σπατάλη και σε κόστος.", "center");

  block(s, ML, 5.0, CW, 1.55,
    "Κρίσιμο σημείο — δεν υπάρχει PTE για μια cache line",
    "Άρα κανείς δεν μπορεί να «μεταναστεύσει γραμμές αντί για σελίδες» μέσα από το λειτουργικό. Η λύση " +
    "είναι είτε έμμεση αναφορά σε υλικό (η τοπική DRAM γίνεται κρυφή μνήμη γραμμών), είτε — και εδώ " +
    "στοχεύει η εργασία — profiling σε λεπτή κοκκομέτρηση (64 B) που οδηγεί αποφάσεις μετανάστευσης σε " +
    "χονδρή (4 KB). Η κοκκομέτρηση profiling διαφέρει από την κοκκομέτρηση migration· αυτό ακριβώς κάνει το M5.",
    true
  );

  s.addNotes("Εδώ θα με ρωτήσουν. Απάντηση: κοκκομέτρηση profiling ≠ κοκκομέτρηση migration. Το M5 profiling στα 64 B, migration στα 4 KB.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 07 — Failure mode 3: migration cost
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(7, "§3.3", "3. Γιατί αποτυγχάνει", "Αστοχία: το κόστος μεταφοράς");

  s.addText("Για να προαχθεί μία σελίδα 4 KB, ο πυρήνας πληρώνει τέσσερα κόστη:", {
    x: ML, y: 1.42, w: CW, h: 0.35, fontFace: SERIF, fontSize: 16, color: INK, margin: 0,
  });

  const costs = [
    ["Αντιγραφή.", "4 KB ανάγνωση από CXL και 4 KB εγγραφή σε DDR — καταναλώνει το εύρος ζώνης που θέλει να σώσει."],
    ["Ενημέρωση πίνακα σελίδων.", "Διάσχιση του rmap για κάθε PTE που χαρτογραφεί τη σελίδα."],
    ["Ακύρωση TLB (shootdown).", "IPI προς κάθε πυρήνα με πιθανή cached μετάφραση — συνήθως το κυρίαρχο κόστος."],
    ["Ανταγωνισμός κλειδωμάτων.", "mmap_lock, LRU locks· δεν παραλληλοποιείται καλά."],
  ];
  costs.forEach(([h, d], i) => {
    const y = 1.95 + i * 0.8;
    const hot = i === 2;
    s.addText(`${i + 1}.`, { x: ML, y, w: 0.4, h: 0.6, fontFace: SERIF, fontSize: 14.5, bold: true, color: hot ? ALERT : NAVY, margin: 0 });
    s.addText(
      [
        { text: h + " ", options: { bold: true, color: hot ? ALERT : INK } },
        { text: d, options: {} },
      ],
      { x: ML + 0.45, y, w: 6.5, h: 0.7, fontFace: SERIF, fontSize: 13.5, color: INK, lineSpacing: 19, align: "justify", margin: 0 }
    );
  });

  block(s, 8.05, 1.95, CW - (8.05 - ML), 3.15, "Τάξη μεγέθους",
    "Μια μετανάστευση σελίδας κοστίζει της τάξης των μικροδευτερολέπτων (μs) — χιλιάδες φορές " +
    "περισσότερο από τα ~250 ns που προσπαθούμε να αποφύγουμε ανά προσπέλαση.\n\n" +
    "Συνέπεια: μια σελίδα πρέπει να ξαναπροσπελαστεί πολλές φορές για να αποσβέσει τη μεταφορά της. " +
    "Γι’ αυτό μια λανθασμένη προαγωγή δεν είναι απλώς άχρηστη — είναι ενεργά επιζήμια.");

  s.addText(
    "Το κόστος αυτό είναι που επιβάλλει ποσόστωση (quota) στο εύρος ζώνης μετανάστευσης και υστέρηση " +
    "(hysteresis) στις αποφάσεις — ώστε ο μηχανισμός να μην καταναλώνει τους πόρους που υποτίθεται ότι σώζει.",
    { x: ML, y: 5.35, w: CW, h: 0.85, fontFace: SERIF, fontSize: 14.5, italic: true, color: MUT, lineSpacing: 21, align: "justify", margin: 0 }
  );

  s.addNotes("Τάξη μεγέθους: μικροδευτερόλεπτα έναντι νανοδευτερολέπτων. Χιλιαπλάσιο κόστος.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 08 — Three papers
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(8, "§4.1", "4. Σχετική βιβλιογραφία", "Τρεις εργασίες, τρεις διαγνώσεις");

  caption(s, ML, 1.4, CW, "Πίνακας 3:", "οι τρεις εργασίες αναφοράς εντοπίζουν διαφορετική ρίζα του ίδιου προβλήματος.");
  booktabs(s, ML, 1.75, [1.95, 4.05, 3.9, 1.83], [
    [hb("Εργασία"), hb("Διάγνωση"), hb("Λύση"), hb("Κοκκομέτρηση")],
    [
      { text: "NeoMem\n(MICRO ’24)", options: { bold: true } },
      "Το profiling είναι αργό και χονδροειδές — διορθώνοντάς το, οι σελίδες 4 KB αρκούν",
      "Count-min sketch μέσα στον ελεγκτή CXL και δυναμικό κατώφλι θερμότητας",
      { text: "4 KB", options: { fontFace: CODE, fontSize: 12 } },
    ],
    [
      { text: "M5\n(ASPLOS ’25)", options: { bold: true, color: NAVY } },
      { text: "Η θερμότητα είναι υπο-σελιδική — το πλήθος προσπελάσεων ανά σελίδα παραπλανά", options: { color: NAVY } },
      { text: "Top-K trackers για σελίδες (HPT) και για λέξεις 64 B (HWT)", options: { color: NAVY } },
      { text: "profiling 64 B\nmigration 4 KB", options: { fontFace: CODE, fontSize: 10.5, bold: true, color: NAVY } },
    ],
    [
      { text: "Memstrata\n(OSDI ’24)", options: { bold: true } },
      "Το tiering σε υλικό λειτουργεί — έως ότου συνυπάρξουν πολλές VM και συγκρουστούν",
      "Χρωματισμός σελίδων και online εκτιμητής επιβράδυνσης",
      { text: "64 B (υλικό)", options: { fontFace: CODE, fontSize: 12 } },
    ],
  ], [0.42, 0.82, 0.82, 0.82]);

  s.addText(
    [
      { text: "Οι τρεις διαγνώσεις διαφωνούν, και αυτό είναι διαφωτιστικό: ", options: { bold: true } },
      { text: "το NeoMem εντοπίζει έλλειψη ανάλυσης στον χρόνο, το M5 έλλειψη ανάλυσης στον χώρο, ενώ το Memstrata δείχνει ότι το πρόβλημα εκδηλώνεται μόνο υπό συστέγαση πολλών φόρτων. Η εργασία εστιάζει στο M5, ως το πλησιέστερο στην υπόθεση της υπο-σελιδικής θερμότητας.", options: {} },
    ],
    { x: ML, y: 5.5, w: CW, h: 1.1, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 22, align: "justify", margin: 0 }
  );

  s.addNotes("Το ότι διαφωνούν είναι δύναμη: δείχνει ότι διάβασα και τις τρεις, όχι μία.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 09 — The honest tradeoff
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(9, "§4.2", "4. Σχετική βιβλιογραφία", "Ο έντιμος συμβιβασμός: σελίδες ή γραμμές;");

  caption(s, ML, 1.35, CW, "Πίνακας 4:", "σύγκριση μετανάστευσης σελίδων (λογισμικό) και caching γραμμών (υλικό).");
  booktabs(s, ML, 1.68, [4.0, 3.8, 3.83], [
    [hb("Ιδιότητα"), hb("Μετανάστευση σελίδων (OS)"), hb("Caching γραμμών (υλικό)")],
    ["Μονάδα", "4 KB / 2 MB", "64 B"],
    ["Ποιος αποφασίζει", "OS, με παρωχημένη πληροφορία", "Υλικό, αντιδραστικά"],
    ["Χαμένη μεταφορά", "Υψηλή", "Σχεδόν μηδενική"],
    ["Σταθερό κόστος ανά κίνηση", { text: "μs (TLB shootdown)", options: { fontFace: CODE, fontSize: 12 } }, { text: "ns", options: { fontFace: CODE, fontSize: 12 } }],
    ["Μεταδεδομένα", "Πίνακες σελίδων (ήδη υπάρχουν)", "Πίνακας ετικετών — τεράστιος"],
    ["Χωρητικότητα", "100% αξιοποιήσιμη", "Γρήγορη βαθμίδα → κρυφή μνήμη"],
    ["Αστοχίες σύγκρουσης", "Δεν υφίστανται", "Ναι — και μεταξύ ενοίκων"],
    ["Νέο υλικό", "Όχι", "Ναι"],
  ], [0.42, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4], { fs: 13 });

  s.addText(
    [
      { text: "Συμπέρασμα: ", options: { bold: true, color: ALERT } },
      { text: "η κοκκομέτρηση γραμμής εξαλείφει τη σπατάλη και το σταθερό κόστος, αλλά αγοράζει αστοχίες σύγκρουσης, αποθήκευση ετικετών και απώλεια της γρήγορης χωρητικότητας ως διευθυνσιοδοτήσιμης μνήμης. Δεν είναι καθαρή νίκη — γι’ αυτό και το πεδίο δεν έχει συγκλίνει.", options: {} },
    ],
    { x: ML, y: 5.7, w: CW, h: 1.0, fontFace: SERIF, fontSize: 14.5, color: INK, lineSpacing: 21, align: "justify", margin: 0 }
  );

  s.addNotes("Αυτή η διαφάνεια ξεχωρίζει το «διάβασα μια εργασία» από το «κατάλαβα το πρόβλημα».");
}

// ═════════════════════════════════════════════════════════════════════════════
// 10 — The tool
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(10, "§5.1", "5. Μεθοδολογία", "Το εργαλείο: CXLRAMSim");

  s.addText(
    "Ο CXLRAMSim είναι προσομοιωτής πλήρους συστήματος πάνω στο gem5 v25, με εκκίνηση Linux 6.14. " +
    "Μοντελοποιεί τη συσκευή CXL στη σωστή θέση πάνω στον δίαυλο I/O, επιτρέποντας αναλλοίωτο πυρήνα, " +
    "οδηγούς και στοίβα λογισμικού.",
    { x: ML, y: 1.45, w: CW, h: 0.9, fontFace: SERIF, fontSize: 16, color: INK, lineSpacing: 24, align: "justify", margin: 0 }
  );

  s.addText("Βασικά δομικά στοιχεία που μοντελοποιεί:", { x: ML, y: 2.45, w: CW, h: 0.32, fontFace: SERIF, fontSize: 14.5, bold: true, color: INK, margin: 0 });
  const comps = [
    ["Firmware.", "πίνακες ACPI (MCFG, DSDT, CEDT, SRAT) για ανακάλυψη της τοπολογίας."],
    ["CXL.io.", "Root Complex και σύνολα καταχωρητών για απαρίθμηση της συσκευής."],
    ["CXL.mem.", "επίπεδο συναλλαγών με κανάλια M2S / S2M και πακετοποίηση στα άκρα."],
    ["Συνοχή.", "πρωτόκολλο MESI δύο επιπέδων με κατανεμημένο κατάλογο (Ruby)."],
  ];
  comps.forEach(([h, d], i) => {
    const y = 2.82 + i * 0.42;
    s.addText("–", { x: ML + 0.1, y, w: 0.3, h: 0.32, fontFace: SERIF, fontSize: 14.5, color: NAVY, margin: 0 });
    s.addText([{ text: h + " ", options: { bold: true, fontFace: CODE, fontSize: 12.5 } }, { text: d, options: {} }],
      { x: ML + 0.45, y, w: CW - 0.45, h: 0.34, fontFace: SERIF, fontSize: 14, color: INK, valign: "middle", margin: 0 });
  });

  block(s, ML, 4.75, CW, 1.75, "Πού παρεμβάλλεται ο κώδικας της εργασίας",
    "Στο σημείο όπου ο κόμβος CXL απο-πακετοποιεί ένα αίτημα M2S σε προσπέλαση της DRAM, διατίθεται η " +
    "πλειάδα {φυσική διεύθυνση, ανάγνωση/εγγραφή, χρονική στιγμή}. Αυτή είναι ακριβώς η ροή αστοχιών " +
    "LLC προς τη CXL την οποία κάνουν profiling τα NeoMem και M5· τίποτε άλλο δεν είναι ορατό από εκεί. " +
    "Ο profiler υλοποιείται ως λήψη (tap) πάνω σε αυτό το μονοπάτι αιτημάτων.");

  s.addNotes("Ανοιχτό θέμα: χρειάζομαι πρόσβαση στο αποθετήριο του CXLRAMSim — δεν βρήκα δημόσιο repo.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 11 — The experiment
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(11, "§5.2", "5. Μεθοδολογία", "Σχέδιο πειράματος");

  s.addText("Πέντε σκέλη σύγκρισης.", { x: ML, y: 1.42, w: 5.6, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  const arms = [
    ["Όλα σε CXL", "κάτω φράγμα"],
    ["Όλα σε τοπική DRAM", "άνω φράγμα"],
    ["Αφελής μετανάστευση σελίδων", "το «πρόβλημα»"],
    ["Σχήμα του M5 (HPT + HWT)", "η πρόταση"],
    ["Oracle τοποθέτηση", "βέλτιστο offline"],
  ];
  arms.forEach(([a, tag], i) => {
    const y = 1.82 + i * 0.44;
    s.addText(`${i + 1}.`, { x: ML, y, w: 0.35, h: 0.3, fontFace: SERIF, fontSize: 14, color: NAVY, margin: 0 });
    s.addText([{ text: a, options: { bold: i === 2 || i === 3 } }, { text: "  — " + tag, options: { italic: true, color: MUT } }],
      { x: ML + 0.4, y, w: 5.4, h: 0.34, fontFace: SERIF, fontSize: 14, color: INK, valign: "middle", margin: 0 });
  });
  s.addText(
    "Η απόσταση μεταξύ του αφελούς σκέλους και του oracle είναι, επακριβώς, το πρόβλημα που αναπαράγεται.",
    { x: ML, y: 4.15, w: 5.6, h: 0.7, fontFace: SERIF, fontSize: 14, italic: true, color: ALERT, lineSpacing: 20, align: "justify", margin: 0 }
  );

  s.addShape(pres.ShapeType.rect, { x: 6.75, y: 1.45, w: 0.01, h: 4.4, fill: { color: RULE } });

  s.addText("Φόρτοι εργασίας.", { x: 7.1, y: 1.42, w: 5.4, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  s.addText(
    [
      { text: "GUPS", options: { fontFace: CODE, fontSize: 12 } }, { text: " — τυχαίες ενημερώσεις 8 B, μηδενική χωρική τοπικότητα (η αντίπαλη περίπτωση)\n", options: {} },
      { text: "XSBench", options: { fontFace: CODE, fontSize: 12 } }, { text: " — αναζητήσεις Monte Carlo σε μεγάλους πίνακες\n", options: {} },
      { text: "PageRank", options: { fontFace: CODE, fontSize: 12 } }, { text: " — άτακτη προσπέλαση γράφου, μετακινούμενο θερμό σύνολο\n", options: {} },
      { text: "Btree / YCSB-C", options: { fontFace: CODE, fontSize: 12 } }, { text: " — κατανομή Zipf, ακραία υπο-σελιδική θερμότητα", options: {} },
    ],
    { x: 7.1, y: 1.8, w: 5.4, h: 1.7, fontFace: SERIF, fontSize: 13.5, color: INK, lineSpacing: 20, margin: 0 }
  );

  s.addText("Μετρικές.", { x: 7.1, y: 3.85, w: 5.4, h: 0.32, fontFace: SERIF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  s.addText(
    [
      { text: "– αθροιστική κατανομή πυκνότητας προσπελάσεων ανά γραμμή 64 B\n", options: {} },
      { text: "– απόδοση μεταφοράς: bytes που μεταφέρθηκαν ÷ bytes που χρησιμοποιήθηκαν\n", options: {} },
      { text: "– επικαιρότητα προαγωγής και ποσοστό σελίδων ακόμη θερμών κατά την προαγωγή\n", options: {} },
      { text: "– επιβράδυνση συναρτήσει του λόγου βαθμίδων· πλήθος ταλαντώσεων (ping-pong)", options: {} },
    ],
    { x: 7.1, y: 4.23, w: 5.4, h: 1.95, fontFace: SERIF, fontSize: 13, color: INK, lineSpacing: 19, margin: 0 }
  );

  s.addNotes("Πάντα αναφέρω και τα δύο φράγματα δίπλα σε κάθε σχήμα — αλλιώς το νούμερο δεν ερμηνεύεται.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 12 — The figure
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(12, "§5.3", "5. Μεθοδολογία", "Το ζητούμενο σχήμα");

  s.addText(
    "Για κάθε σελίδα 4 KB μετράμε τι ποσοστό των προσπελάσεών της συγκεντρώνεται στις k θερμότερες " +
    "γραμμές των 64 B. Αν το 80% των προσπελάσεων πέφτει σε λιγότερο από το 10% της σελίδας, το " +
    "επιχείρημα της κοκκομέτρησης αποδεικνύεται σε ένα και μόνο διάγραμμα (Σχήμα 3).",
    { x: ML, y: 1.45, w: 5.15, h: 1.6, fontFace: SERIF, fontSize: 15, color: INK, lineSpacing: 23, align: "justify", margin: 0 }
  );

  s.addText(
    [
      { text: "Επιφύλαξη. ", options: { bold: true, color: ALERT } },
      { text: "Η καμπύλη είναι η αναμενόμενη μορφή, όχι μετρημένα δεδομένα· ο προσομοιωτής δεν έχει ακόμη εκτελεστεί. Αν βγει επίπεδη, το επιχείρημα της υπο-σελιδικής θερμότητας καταρρέει για τον φόρτο αυτόν — αποτέλεσμα εξίσου χρήσιμο.", options: {} },
    ],
    { x: ML, y: 3.25, w: 5.15, h: 1.9, fontFace: SERIF, fontSize: 14, color: INK, lineSpacing: 21, align: "justify", margin: 0 }
  );

  const cats = ["1", "4", "8", "16", "24", "32", "48", "64"];
  s.addChart(
    pres.ChartType.line,
    [
      { name: "Zipf (Btree / YCSB)", labels: cats, values: [31, 62, 78, 88, 93, 96, 99, 100] },
      { name: "Ομοιόμορφη (GUPS)", labels: cats, values: [2, 6, 13, 25, 38, 50, 75, 100] },
    ],
    {
      x: 6.35, y: 1.5, w: 6.13, h: 4.05,
      showTitle: false,
      chartColors: [NAVY, ALERT], lineSize: 2.25, lineSmooth: true,
      lineDash: ["solid", "dash"],
      showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: INK, legendFontFace: SERIF,
      catAxisTitle: "k θερμότερες γραμμές 64 B (από 64)", showCatAxisTitle: true, catAxisTitleFontSize: 11, catAxisTitleColor: MUT, catAxisTitleFontFace: SERIF,
      valAxisTitle: "αθροιστικό %", showValAxisTitle: true, valAxisTitleFontSize: 11, valAxisTitleColor: MUT, valAxisTitleFontFace: SERIF,
      catAxisLabelColor: INK, valAxisLabelColor: INK, catAxisLabelFontFace: SERIF, valAxisLabelFontFace: SERIF,
      catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
      valAxisMaxVal: 100, valAxisMinVal: 0, valAxisMajorUnit: 25,
      valGridLine: { color: "E3E3E3", size: 1 }, catGridLine: { style: "none" },
    }
  );
  caption(s, 6.35, 5.65, 6.13, "Σχήμα 3:", "αθροιστικό ποσοστό προσπελάσεων στις k θερμότερες γραμμές 64 B (αναμενόμενη μορφή).", "center");

  s.addNotes("Σκίτσο, όχι δεδομένα — και το δηλώνω. Ο Zipf δείχνει ακραία συγκέντρωση· το GUPS είναι αρνητικός έλεγχος.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 13 — Timeline
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(13, "§6.1", "6. Πλάνο & συζήτηση", "Φάσεις υλοποίησης και διαχείριση ρίσκου");

  const phases = [
    ["Φάση 1.", "Εκκίνηση και checkpoint.", "Boot έως shell, επιβεβαίωση κόμβου zNUMA, microbenchmark καθυστέρησης («απόδειξη ότι η CXL είναι αργή»)."],
    ["Φάση 2.", "Λήψη ιχνών προσπέλασης.", "Σημείο λήψης στη ροή αιτημάτων της συσκευής και κατανομή πυκνότητας — το πρώτο πραγματικό αποτέλεσμα."],
    ["Φάση 3.", "Βασική γραμμή μετανάστευσης.", "Αφελής μετανάστευση σελίδων με έντιμο μοντέλο κόστους και ποσόστωση εύρους ζώνης."],
    ["Φάση 4.", "Υλοποίηση M5.", "Πρώτα ο HPT (θερμές σελίδες), κατόπιν ο HWT (θερμές λέξεις 64 B) ως το διαφοροποιητικό στοιχείο."],
    ["Φάση 5.", "Αξιολόγηση και συγγραφή.", "Ανάλυση ευαισθησίας ως προς K, διάστημα, ποσόστωση και καθυστέρηση CXL."],
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
    "Η Φάση 2 απομειώνει το ρίσκο όλων των υπολοίπων, παράγοντας παρουσιάσιμο αποτέλεσμα πριν γραφτεί " +
    "οποιαδήποτε πολιτική. Προαιρετικές επεκτάσεις: μοντέλο κόστους υλικού, σάρωση καθυστέρησης, δύο συντρέχοντες φόρτοι.",
    { x: ML, y: 5.75, w: CW, h: 0.8, fontFace: SERIF, fontSize: 14, italic: true, color: MUT, lineSpacing: 21, align: "justify", margin: 0 }
  );

  s.addNotes("Δηλώνω ξεκάθαρα τι είναι βασικό και τι stretch goal.");
}

// ═════════════════════════════════════════════════════════════════════════════
// 14 — Open questions
// ═════════════════════════════════════════════════════════════════════════════
{
  const s = frame(14, "§6.2", "6. Πλάνο & συζήτηση", "Ανοιχτά ερωτήματα προς συζήτηση");

  const qs = [
    ["Πρόσβαση στον CXLRAMSim.", "Υπάρχει διαθέσιμο αποθετήριο και οδηγίες build; Ιδανικά και έτοιμο disk image — το χτίσιμο από το μηδέν είναι παράκαμψη ημερών που δεν διδάσκει τίποτε για το tiering."],
    ["Κλίμακα φόρτων.", "Είναι αποδεκτό να μειωθεί το μέγεθος σε εκατοντάδες MB αντί για 10–20 GB RSS, διατηρώντας ρεαλιστικό τον λόγο των βαθμίδων;"],
    ["Εύρος υλοποίησης.", "Αρκεί profiler HPT+HWT με μοντελοποιημένη μηχανή μετανάστευσης, ή ζητείται πραγματική μετανάστευση Linux οδηγούμενη από kernel module;"],
    ["Επιλογή εργασίας.", "Είναι το M5 η ενδεδειγμένη επιλογή, ή προτιμάται υλοποίηση του NeoMem;"],
  ];
  qs.forEach(([h, d], i) => {
    const y = 1.55 + i * 1.05;
    s.addText(`${i + 1}.`, { x: ML, y, w: 0.45, h: 0.32, fontFace: SERIF, fontSize: 16, bold: true, color: NAVY, margin: 0 });
    s.addText(h, { x: ML + 0.5, y, w: CW - 0.5, h: 0.34, fontFace: SERIF, fontSize: 16, bold: true, color: INK, margin: 0 });
    s.addText(d, { x: ML + 0.5, y: y + 0.36, w: CW - 0.5, h: 0.6, fontFace: SERIF, fontSize: 14, color: INK, lineSpacing: 20, align: "justify", margin: 0 });
  });

  s.addNotes(
    "Έτοιμη απάντηση για «γιατί όχι απευθείας cache lines»: δεν υπάρχει PTE για γραμμή → έμμεση " +
    "αναφορά σε υλικό → Flat Memory Mode → κοστίζει αστοχίες σύγκρουσης και χωρητικότητα → αυτό ακριβώς λύνει το Memstrata."
  );
}

const out = path.join(__dirname, "..", "docs", "memory-tiering-cxl-gr.pptx");
pres.writeFile({ fileName: out }).then(() => console.log("wrote " + out));
