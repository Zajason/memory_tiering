/* build_signal_el.mjs -- Greek 15-slide CSLab talk, Bauhaus Signal palette.
 *
 * Rebuilt with pptxgenjs because the Presenton "Signal Edition" of 1 Nov 2026
 * is no longer retrievable: its download and preview links were 24-hour and
 * expired on 2 Nov, and presenton-signal.md records that the source HTML lived
 * only in a temporary directory and was deleted after delivery. This keeps that
 * edition's declared design -- #185ADB / #F04438 / #F5C542 / #171717, fifteen
 * slides, and the six original plots preserved uncropped -- rather than
 * silently restoring the older paper/black/red local style, which the
 * presentation README explicitly forbids.
 *
 * Every number here is copied from verified outputs:
 *   results/fidelity-2026-10-27/scores.csv        real-input fidelity + controls
 *   docs/audit-2026-10.md                         audit findings and withdrawals
 *   results/fidelity-stage2-2026-10-28/campaign.json   18/21, multithread hold
 *   results/revalidated-2026-10-25/...            simulator + trackers
 *
 * Run:  ~/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
 *         presentation/build_signal_el.mjs
 */
import path from 'node:path';
import {existsSync, readFileSync} from 'node:fs';
import {createRequire} from 'node:module';

const RUNTIME = process.env.CODEX_RUNTIME ||
  `${process.env.HOME}/.cache/codex-runtimes/codex-primary-runtime/dependencies`;
const require = createRequire(`${RUNTIME}/node/node_modules/`);
const PptxGenJS = require('pptxgenjs');

const REPO = path.resolve(import.meta.dirname, '..');

/* The liblinear simulator run writes its summary every epoch, so its window
 * count climbs while the run continues. Read it at build time rather than
 * hardcoding: the deck said 61 within hours of being built, when the run had
 * already reached 81. */
function liblinearWindows() {
  const f = path.join(REPO,
    'results/revalidated-2026-10-25/sim/liblinear/attempt-1/hotskew-liblinear.bridge');
  if (!existsSync(f)) return null;
  const m = readFileSync(f, 'utf8').match(/^epochs\s+(\d+)/m);
  return m ? Number(m[1]) : null;
}
const LIB_WINDOWS = liblinearWindows();
const OUT = path.join(REPO, 'presentation', 'CSLab_Memory_Tiering_Signal_EL.pptx');

/* ---- Bauhaus Signal, as declared in presenton-signal.md ---- */
const C = {
  blue:  '185ADB',
  red:   'F04438',
  amber: 'F5C542',
  ink:   '171717',
  white: 'FFFFFF',
  paper: 'F7F7F5',
  grey:  '6B6B6B',
  line:  'D8D8D4',
};
const F = {disp: 'League Spartan', tech: 'IBM Plex Sans', el: 'Noto Sans'};

const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_16x9';           // 10 x 5.625 in
pptx.author = 'Ιάσων Ζακυνθινός';
pptx.title = 'Hot skewness σε επίπεδο cache line για CXL memory tiering';
const W = 10, H = 5.625;

/* Each helper builds its own fill/shadow objects: pptxgenjs mutates them. */
const band = (s, y, h, color) =>
  s.addShape(pptx.ShapeType.rect, {x: 0, y, w: W, h, fill: {color}, line: {width: 0}});

/* Greek orthography drops the monotonic accent in all-caps; JS toUpperCase()
 * keeps it, which produces "ΤΟ ΠΡΌΒΛΗΜΑ" instead of "ΤΟ ΠΡΟΒΛΗΜΑ". A Greek
 * reader notices immediately, so uppercase goes through here. The dialytika is
 * preserved, since it is not an accent. */
const GREEK_UPPER = {'ά':'Α','έ':'Ε','ή':'Η','ί':'Ι','ό':'Ο','ύ':'Υ','ώ':'Ω',
  'Ά':'Α','Έ':'Ε','Ή':'Η','Ί':'Ι','Ό':'Ο','Ύ':'Υ','Ώ':'Ω',
  'ΐ':'Ϊ','ΰ':'Ϋ','ϊ':'Ϊ','ϋ':'Ϋ'};
const elUpper = t => t.replace(/[άέήίόύώΆΈΉΊΌΎΏΐΰϊϋ]/g, c => GREEK_UPPER[c]).toUpperCase();

function titleBar(s, kicker, title, dark = false) {
  band(s, 0, 1.18, dark ? C.ink : C.white);
  s.addShape(pptx.ShapeType.rect, {x: 0, y: 0, w: 0.09, h: 1.18,
    fill: {color: C.red}, line: {width: 0}});
  s.addText(elUpper(kicker), {x: 0.42, y: 0.17, w: 8.9, h: 0.26,
    fontFace: F.tech, fontSize: 11, bold: true, charSpacing: 2,
    color: dark ? C.amber : C.blue, margin: 0});
  s.addText(title, {x: 0.42, y: 0.44, w: 9.1, h: 0.62,
    fontFace: F.el, fontSize: 25, bold: true,
    color: dark ? C.white : C.ink, margin: 0});
}

function newSlide(kicker, title, {dark = false} = {}) {
  const s = pptx.addSlide();
  band(s, 0, H, dark ? C.ink : C.paper);
  titleBar(s, kicker, title, dark);
  return s;
}

function notes(s, t) { s.addNotes(t); }

/* bullets: array of strings, or [text, sub] pairs */
function bullets(s, items, {x = 0.5, y = 1.5, w = 9, dark = false, size = 15} = {}) {
  const runs = [];
  items.forEach((it, i) => {
    const [main, sub] = Array.isArray(it) ? it : [it, null];
    runs.push({text: main, options: {bullet: true, fontFace: F.el, fontSize: size,
      bold: !!sub, color: dark ? C.white : C.ink, breakLine: true,
      paraSpaceBefore: i ? 7 : 0}});
    if (sub) runs.push({text: sub, options: {fontFace: F.el, fontSize: size - 2.5,
      color: dark ? 'B9B9B4' : C.grey, indentLevel: 1, breakLine: true}});
  });
  s.addText(runs, {x, y, w, h: H - y - 0.35, margin: 0, valign: 'top'});
}

function metricRow(s, cards, {y = 1.65, h = 1.5} = {}) {
  const gap = 0.22, w = (9 - gap * (cards.length - 1)) / cards.length;
  cards.forEach((c, i) => {
    const x = 0.5 + i * (w + gap);
    s.addShape(pptx.ShapeType.rect, {x, y, w, h,
      fill: {color: C.white}, line: {color: C.line, width: 1}});
    s.addShape(pptx.ShapeType.rect, {x, y, w, h: 0.07,
      fill: {color: c.accent || C.blue}, line: {width: 0}});
    s.addText(c.big, {x: x + 0.12, y: y + 0.22, w: w - 0.24, h: 0.58,
      fontFace: F.disp, fontSize: 30, bold: true, color: c.accent || C.blue,
      align: 'center', margin: 0});
    s.addText(c.label, {x: x + 0.12, y: y + 0.82, w: w - 0.24, h: h - 0.92,
      fontFace: F.el, fontSize: 10.5, color: C.grey, align: 'center', margin: 0});
  });
}

/* object-fit: contain, never cropped -- these are the preserved evidence plots */
function figure(s, rel, {y = 1.35, h = 3.5, caption = null} = {}) {
  const p = path.join(REPO, rel);
  if (!existsSync(p)) { console.warn('MISSING FIGURE', rel); return; }
  s.addImage({path: p, x: 0.5, y, w: 9, h, sizing: {type: 'contain', w: 9, h}});
  if (caption) s.addText(caption, {x: 0.5, y: y + h + 0.06, w: 9, h: 0.42,
    fontFace: F.el, fontSize: 9.5, color: C.grey, align: 'center', margin: 0});
}

function dataTable(s, head, rows, {y = 1.5, colW, highlight = []} = {}) {
  const body = [[...head.map(t => ({text: t, options: {bold: true, color: C.white,
    fill: {color: C.ink}, fontFace: F.tech, fontSize: 11}}))]];
  rows.forEach((r, ri) => {
    const hot = highlight.includes(ri);
    body.push(r.map((cell, ci) => ({text: String(cell), options: {
      fontFace: ci === 0 ? F.el : F.tech, fontSize: 11.5,
      bold: hot, color: hot ? C.blue : C.ink,
      fill: {color: hot ? 'EAF1FD' : C.white},
      align: ci === 0 ? 'left' : 'right'}})));
  });
  s.addTable(body, {x: 0.5, y, w: 9, colW, border: {type: 'solid', color: C.line, pt: 0.5},
    rowH: 0.3, valign: 'middle'});
}

/* ===================== 1. cover ===================== */
{
  const s = pptx.addSlide();
  band(s, 0, H, C.ink);
  // geometric cover
  s.addShape(pptx.ShapeType.rect, {x: 0, y: 0, w: 0.5, h: H, fill: {color: C.blue}, line: {width: 0}});
  s.addShape(pptx.ShapeType.ellipse, {x: 7.5, y: -0.9, w: 3.3, h: 3.3,
    fill: {color: C.red}, line: {width: 0}});
  s.addShape(pptx.ShapeType.rect, {x: 8.55, y: 4.1, w: 1.45, h: 1.45,
    fill: {color: C.amber}, line: {width: 0}});
  s.addText('HOT SKEWNESS', {x: 1.0, y: 1.42, w: 7, h: 0.5,
    fontFace: F.disp, fontSize: 15, bold: true, charSpacing: 5, color: C.amber, margin: 0});
  s.addText('Αναπαραγωγή του Figure 4 του M5\nσε επίπεδο cache line', {
    x: 1.0, y: 1.95, w: 7.3, h: 1.5, fontFace: F.el, fontSize: 30, bold: true,
    color: C.white, lineSpacing: 34, margin: 0});
  s.addText('Δικό μας pintool · μοντέλο cache · full-system CXL προσομοίωση · μετρητές PAC/WAC',
    {x: 1.0, y: 3.5, w: 7.3, h: 0.5, fontFace: F.el, fontSize: 13, color: 'B9B9B4', margin: 0});
  s.addText('Ιάσων Ζακυνθινός  ·  ΕΜΠ / CSLab  ·  Νοέμβριος 2026', {
    x: 1.0, y: 4.5, w: 7.3, h: 0.35, fontFace: F.tech, fontSize: 11.5, color: C.white, margin: 0});
  notes(s, 'Καλημέρα. Θα δείξω τη δουλειά στην αναπαραγωγή του Figure 4 του M5: '
    + 'το εργαλείο που έφτιαξα, τι αναπαράγεται και τι όχι, και τι χρειάζομαι για να κλείσει το κενό. '
    + '15 λεπτά, 15 διαφάνειες.');
}

/* ===================== 2. the problem ===================== */
{
  const s = newSlide('Το πρόβλημα', 'Η σελίδα 4 KB είναι λάθος μονάδα');
  bullets(s, [
    ['CXL: φθηνή χωρητικότητα, ~2.2x latency', 'Δύο βαθμίδες μνήμης — κάποιος πρέπει να αποφασίσει τι μένει πού.'],
    ['Το λειτουργικό μετακινεί σελίδες 4 KB', 'Το υλικό όμως φέρνει γραμμές 64 B. 64 words ανά σελίδα.'],
    ['Το M5 (ASPLOS ’25) δείχνει ότι οι προσβάσεις συγκεντρώνονται', 'Σε λίγα words της σελίδας — άρα μετακινούμε κυρίως κρύα bytes.'],
  ], {y: 1.45});
  metricRow(s, [
    {big: '4 KB', label: 'μονάδα μετακίνησης\nτου λειτουργικού', accent: C.blue},
    {big: '64 B', label: 'μονάδα πρόσβασης\nτου υλικού', accent: C.red},
    {big: '64', label: 'words ανά σελίδα —\nπόσα είναι «hot»;', accent: C.amber},
  ], {y: 3.6, h: 1.6});
  notes(s, 'Το CXL δίνει χωρητικότητα με κόστος καθυστέρησης. Η απόφαση τοποθέτησης γίνεται '
    + 'σε σελίδες 4 KB, αλλά το υλικό δουλεύει σε γραμμές 64 B. Το M5 υποστηρίζει ότι αυτή η '
    + 'αναντιστοιχία σπαταλά bandwidth, και το Figure 4 είναι η απόδειξη.');
}

/* ===================== 3. the assignment ===================== */
{
  const s = newSlide('Το ζητούμενο', 'Τι ακριβώς ζητήθηκε — και τι είναι το Figure 4');
  bullets(s, [
    ['1. Αναπαραγωγή του hot skewness σε επίπεδο cache line', 'Όχι σε επίπεδο σελίδας — αυτό είναι το Figure 3 (ANB/DAMON).'],
    ['2. Pintool που παρακολουθεί memory references', 'Επιβεβαιώθηκε από το paper: Figure 4 = «P(σελίδα 4 KB αγγίζει το πολύ N μοναδικά 64 B words)».'],
    ['3. Benchmark από το artifact evaluation', 'GAPBS, Redis/YCSB, Memcached, liblinear.'],
  ], {y: 1.45});
  s.addShape(pptx.ShapeType.rect, {x: 0.5, y: 3.5, w: 9, h: 1.25,
    fill: {color: C.white}, line: {color: C.blue, width: 1.5}});
  s.addText([
    {text: 'Η μετρική, με μια γραμμή:  ', options: {fontFace: F.el, fontSize: 13, bold: true, color: C.ink}},
    {text: 'για κάθε σελίδα μετράμε πόσα από τα 64 words της αγγίχτηκαν μέσα σε ένα '
      + 'measurement window, και σχεδιάζουμε το CDF στα N = 4, 8, 16, 32, 48.',
      options: {fontFace: F.el, fontSize: 13, color: C.ink}},
  ], {x: 0.75, y: 3.68, w: 8.5, h: 0.95, margin: 0, valign: 'top'});
  notes(s, 'Τρία πράγματα ζητήθηκαν. Επιβεβαίωσα από το κείμενο του paper ότι το Figure 4 '
    + 'είναι το σωστό σχήμα — το Figure 3 είναι άλλο πράγμα, αφορά ANB και DAMON σε επίπεδο σελίδας.');
}

/* ===================== 4. the pintool ===================== */
{
  const s = newSlide('Το εργαλείο', 'Γιατί έφτιαξα δικό μου pintool', {dark: true});
  bullets(s, [
    ['Κανένα έτοιμο pintool δεν κρατάει ποια words αγγίζονται', 'Το pinatrace δίνει διευθύνσεις, το dcache hits/misses. Κανένα δεν δίνει τη word mask ανά σελίδα.'],
    ['Post-processing πλήρους trace: ανέφικτο', 'Μόνο το sssp κάνει 6.3 δισ. memory references — εκατοντάδες GB ανά workload.'],
    ['Άρα: η καταμέτρηση γίνεται μέσα στο tool, σε ένα πέρασμα', '~1.650 γραμμές C++. Instrumentation (μία φορά) vs analysis (κάθε εκτέλεση) — το κρίσιμο μοτίβο του Pin.'],
    ['Κόστος ενεργοποίησης: ένα predicated load', 'InsertIfCall(isActive) + InsertThenCall — ο ακριβός δρόμος καλείται μόνο όταν μετράμε.'],
  ], {y: 1.45, dark: true});
  notes(s, 'Η καθηγήτρια είπε «υπάρχουν πολλά εκεί έξω» — και είναι αλήθεια, αλλά κανένα δεν '
    + 'κρατάει ποια 64 B words αγγίζονται μέσα στη σελίδα. Θα μπορούσα να κάνω post-process '
    + 'ένα trace, αλλά τα μεγέθη είναι απαγορευτικά. Οπότε η καταμέτρηση μπήκε μέσα στο tool.');
}

/* ===================== 5. the cache model ===================== */
{
  const s = newSlide('Το μοντέλο cache', 'Γιατί χρειάζεται — και τι σημαίνει «miss»');
  bullets(s, [
    ['Οι μετρητές του M5 είναι στον CXL controller', 'Βλέπουν μόνο ό,τι φτάνει στη μνήμη. Πάνω από 97% των references δεν φεύγει ποτέ από το chip.'],
    ['Μοντέλο Sapphire Rapids: L1d 48 KB/12, L2 2 MB/16, L3 40 MB/10 ways', 'Set-associative, true LRU, writeback, write-allocate, non-inclusive. Το CAT κατατέμνει κατά ways, άρα το associativity το αναπαράγει ακριβώς.'],
  ], {y: 1.45});
  s.addShape(pptx.ShapeType.rect, {x: 0.5, y: 2.75, w: 9, h: 1.95,
    fill: {color: C.white}, line: {color: C.line, width: 1}});
  s.addText(elUpper('Τρία streams — ορισμοί που δηλώθηκαν εκ των προτέρων'), {
    x: 0.72, y: 2.9, w: 8.6, h: 0.26, fontFace: F.tech, fontSize: 10.5, bold: true,
    charSpacing: 1.5, color: C.blue, margin: 0});
  bullets(s, [
    ['accesses — κάθε memory operand του χρήστη', 'πριν από οποιοδήποτε φιλτράρισμα cache'],
    ['fills — demand misses στο LLC', 'ό,τι πραγματικά ζητείται από τη μνήμη'],
    ['traffic — fills + dirty writebacks', 'ό,τι θα έβλεπε ένας μετρητής στη μνήμη'],
  ], {x: 0.72, y: 3.2, w: 8.6, size: 12.5});
  notes(s, 'Αυτό είναι το σημείο που συχνά παραβλέπεται: το Pin δίνει κάθε load και store, '
    + 'αλλά οι μετρητές του M5 βλέπουν μόνο ό,τι φτάνει στη μνήμη. Το μοντέλο cache είναι το '
    + 'φίλτρο. Δηλώσαμε τρία streams εκ των προτέρων ώστε να μη διαλέγουμε εκ των υστέρων.');
}

/* ===================== 6. calibration ===================== */
{
  const s = newSlide('Βαθμονόμηση', 'Πρώτα το όργανο, μετά τα αποτελέσματα');
  figure(s, 'docs/assets/hero_validation.png', {y: 1.35, h: 2.55,
    caption: 'Συνθετικά μοτίβα με αναλυτικά γνωστή απάντηση — τέσσερις τάξεις μεγέθους.'});
  dataTable(s, ['Stride', 'Μετρήθηκε', 'Αναλυτικά'], [
    ['64 B', '63.981', '64'],
    ['256 B', '15.996', '16'],
    ['1024 B', '3.999', '4'],
    ['4096 B', '1.000', '1'],
  ], {y: 4.08, colW: [3, 3, 3]});
  notes(s, 'Κανένα αποτέλεσμα δεν έχει νόημα αν το όργανο δεν είναι βαθμονομημένο. '
    + 'Το έτρεξα σε μοτίβα όπου ξέρω αναλυτικά την απάντηση: συμφωνεί σε τέσσερις τάξεις μεγέθους.');
}

/* ===================== 7. the main reproduction ===================== */
{
  const s = newSlide('Κύριο αποτέλεσμα', 'Figure 4: ένα window definition, έξι workloads');
  figure(s, 'docs/assets/fig4_uniform_full.png', {y: 1.3, h: 3.55,
    caption: 'Window: 10M modeled memory events. Η κάτω σειρά χωρίς writebacks. '
      + 'Οπτική συμφωνία δεν είναι replication — οι ακριβείς είσοδοι και το πρωτόκολλο του paper παραμένουν άγνωστα.'});
  notes(s, 'Αυτή είναι η κύρια διαφάνεια. Ένα window definition για όλα τα workloads — '
    + 'η προηγούμενη έκδοση ανακάτευε δύο διαφορετικά window definitions, που κολάκευε τρία workloads. '
    + 'Δεν επιλέχθηκε κανένα window με βάση την καμπύλη αναφοράς.');
}

/* ===================== 8. accesses vs misses ===================== */
{
  const s = newSlide('Accesses vs misses', 'Τα τρία streams δίνουν σχεδόν το ίδιο — και γιατί');
  figure(s, 'docs/assets/fig4_fidelity_full.png', {y: 1.28, h: 2.5});
  dataTable(s, ['BFS, πραγματικό dataset', 'max |σφάλμα|'], [
    ['accesses', '0.5554'],
    ['fills (demand misses)', '0.5556'],
    ['traffic (fills + writebacks)', '0.5547'],
  ], {y: 3.95, colW: [6, 3]});
  s.addText('Αιτία: first-touch misses. Σε ολόκληρο το ROI κάθε γραμμή που αγγίζεται αστοχεί '
    + 'τουλάχιστον μία φορά, άρα το word coverage συγκλίνει — παρά τις πολύ διαφορετικές συχνότητες '
    + 'γεγονότων (933M accesses έναντι 62M fills στο BFS).', {
    x: 0.5, y: 4.95, w: 9, h: 0.55, fontFace: F.el, fontSize: 10.5, color: C.grey, margin: 0});
  notes(s, 'Σημαντικό εύρημα και εύκολο να παρεξηγηθεί: τα τρία streams δίνουν σχεδόν ταυτόσημη '
    + 'coverage, όχι επειδή η cache δεν μετράει, αλλά επειδή σε ολόκληρο το ROI κάθε γραμμή αστοχεί '
    + 'τουλάχιστον μία φορά. Οι συχνότητες γεγονότων διαφέρουν δραματικά — 933 εκατ. έναντι 62 εκατ.');
}

/* ===================== 9. real datasets ===================== */
{
  const s = newSlide('Πραγματικά datasets', 'Twitter WWW2010 και Google+ IMC12 — όχι συνθετικοί γράφοι');
  dataTable(s, ['Workload', 'max |σφάλμα|', 'P(≤16)', 'events'], [
    ['PageRank  (Twitter)', '0.015', '0.000', '7.04 δισ.'],
    ['Triangle counting  (Twitter)', '0.349', '0.202', '170 εκατ.'],
    ['Connected components  (Twitter)', '0.489', '0.417', '79 εκατ.'],
    ['BFS  (Twitter)', '0.555', '0.679', '78 εκατ.'],
    ['Betweenness  (Google+)', '0.772', '0.691', '588 εκατ.'],
    ['SSSP  (Google+)', '0.796', '0.754', '176 εκατ.'],
  ], {y: 1.5, colW: [4.2, 1.7, 1.5, 1.6], highlight: [0]});
  s.addShape(pptx.ShapeType.rect, {x: 0.5, y: 3.75, w: 9, h: 1.0,
    fill: {color: 'EAF1FD'}, line: {color: C.blue, width: 1}});
  s.addText([
    {text: 'Το PageRank αναπαράγεται — 0.015 σε 7 δισεκατομμύρια memory events. ',
      options: {fontFace: F.el, fontSize: 13, bold: true, color: C.blue}},
    {text: 'Τα άλλα πέντε όχι, και το κενό δεν εξηγείται από το dataset: αυτά ΕΙΝΑΙ τα '
      + 'πραγματικά datasets που ονομάζει το artifact.', options: {fontFace: F.el, fontSize: 13, color: C.ink}},
  ], {x: 0.75, y: 3.93, w: 8.5, h: 0.72, margin: 0, valign: 'top'});
  notes(s, 'Εδώ είναι η ουσία. Βρήκα ότι το artifact ονομάζει Google+ και Twitter, όχι web-Google '
    + 'που είχα δοκιμάσει αρχικά. Με τα πραγματικά datasets το PageRank πέφτει στο 0.015 — '
    + 'αναπαράγεται. Τα άλλα πέντε όχι. Άρα το dataset δεν είναι η εξήγηση.');
}

/* ===================== 10. controls ===================== */
{
  const s = newSlide('Controls', 'Τι δοκιμάστηκε και ΔΕΝ κλείνει το κενό', {dark: true});
  dataTable(s, ['Control', 'BFS', 'CC'], [
    ['βάση (1 thread, 1 trial)', '0.555', '0.489'],
    ['20 threads, όπως το paper', '0.590', '0.494'],
    ['warm setup (ζεστές caches)', '0.591', '0.510'],
    ['3 trials', '0.562', '0.492'],
    ['200 trials', '0.596', '0.580'],
    ['9 αντί 10 LLC ways', '≤ 0.043 μεταβολή', '—'],
  ], {y: 1.5, colW: [5.4, 1.8, 1.8]});
  s.addText('Κανένα control δεν μετακινεί το αποτέλεσμα ουσιαστικά. Το κενό δεν είναι '
    + 'thread count, δεν είναι warm-up, δεν είναι trials, δεν είναι η χωρητικότητα του LLC.', {
    x: 0.5, y: 3.95, w: 9, h: 0.6, fontFace: F.el, fontSize: 13, bold: true,
    color: C.amber, margin: 0});
  s.addText('Απομένει το collection protocol του Figure 4: region cycling, reset intervals, '
    + 'αν μετρώνται σελίδες με μηδενικές προσβάσεις, αν περιλαμβάνεται το setup. '
    + 'Το paper δεν τα δηλώνει.', {
    x: 0.5, y: 4.55, w: 9, h: 0.7, fontFace: F.el, fontSize: 12, color: 'B9B9B4', margin: 0});
  notes(s, 'Αυτή είναι η διαφάνεια που θα ρωτήσει. Δοκίμασα συστηματικά: 20 threads όπως το paper, '
    + 'warm setup, 3 και 200 trials, 9 αντί 10 ways. Τίποτα δεν κλείνει το κενό. '
    + 'Ό,τι μένει είναι το collection protocol, που δεν δημοσιεύεται.');
}

/* ===================== 11. PAC/WAC + trackers ===================== */
{
  const s = newSlide('Μετρητές M5', 'PAC / WAC και οι bounded trackers HPT / HWT');
  bullets(s, [
    ['PAC / WAC: ακριβείς μετρητές ανά σελίδα και ανά 64 B word', 'Υλοποιήθηκαν πλήρως — 160 B ανά σελίδα, popcount της μάσκας δίνει τη μετρική του Figure 4.'],
    ['HPT / HWT: top-K με πεπερασμένο budget', 'Space-Saving και Count-Min Sketch, K=128, budgets 50 έως 8192 — σε ξεχωριστές εκτελέσεις.'],
    ['Το PAC είναι το ground truth που βαθμολογεί το HPT', 'Αυτό που κανένα πραγματικό υλικό δεν μπορεί να έχει — και γι’ αυτό το μετράμε σε software.'],
  ], {y: 1.45});
  figure(s, 'results/revalidated-2026-10-25/figures/trackers.png', {y: 3.15, h: 2.2});
  notes(s, 'Πέρα από το σχήμα, υλοποίησα και τους μετρητές που προτείνει το M5. Το PAC/WAC '
    + 'είναι ακριβές, το HPT/HWT είναι το ρεαλιστικό υλικό. Το ενδιαφέρον είναι ότι το ακριβές '
    + 'PAC είναι αυτό που μας επιτρέπει να βαθμολογήσουμε το HPT — κάτι που το υλικό δεν μπορεί.');
}

/* ===================== 12. granularity ===================== */
{
  const s = newSlide('Granularity', 'Page size επί word size, ως επιφάνεια');
  figure(s, 'results/revalidated-2026-10-25/figures/granularity.png', {y: 1.32, h: 3.3,
    caption: 'Ακριβές re-bucketing των παρατηρημένων virtual addresses. '
      + 'ΔΕΝ αποδεικνύει κατανομή huge pages από το λειτουργικό ούτε σπατάλη migration στο υλικό.'});
  notes(s, 'Επέκταση πέρα από το ζητούμενο: τι γίνεται αν αλλάξουμε τη granularity. '
    + 'Προσοχή στη διατύπωση — είναι ακριβές re-bucketing των διευθύνσεων που παρατηρήσαμε, '
    + 'δεν είναι απόδειξη για huge pages.');
}

/* ===================== 13. CXL simulator ===================== */
{
  const s = newSlide('Full-system CXL', 'Από το Pin στον προσομοιωτή — φυσικές διευθύνσεις, ορατό kernel');
  bullets(s, [
    ['Το CXLRAMSim δεν έχει κυκλοφορήσει — πήγαμε σε SimCXL / CXL-DMSim (gem5 23.1)', 'Ο ίδιος κώδικας καταμέτρησης, χωρίς αλλαγή: μία κλήση ανά request.'],
    ['Μέτρηση στη θύρα της συσκευής CXL και στον controller πίσω της', 'Τα ιστογράμματα συμφωνούν — ίδια κατανομή, άρα η θέση του μετρητή δεν αλλάζει το αποτέλεσμα.'],
    ['Έξι graph workloads ολοκληρωμένα και ελεγμένα', `liblinear: ενεργό, ${LIB_WINDOWS ?? '—'} windows × 10M events μέχρι τη στιγμή της `
      + 'μέτρησης — μερικό, και δηλώνεται ως μερικό.'],
  ], {y: 1.45});
  figure(s, 'results/revalidated-2026-10-25/sim-comparison/figure4-m5-pin-simulator.png',
    {y: 3.25, h: 2.1});
  notes(s, 'Το CXLRAMSim δεν έχει βγει, οπότε χρησιμοποίησα το SimCXL. Το σημαντικό: ο κώδικας '
    + 'καταμέτρησης μεταφέρθηκε αυτούσιος, και μετρώντας ταυτόχρονα στη θύρα CXL και στον '
    + 'controller πίσω της πήραμε ταυτόσημα ιστογράμματα. Το liblinear τρέχει ακόμα — '
    + 'το αναφέρω ως μερικό, δεν θα ολοκληρωθεί σε εύλογο χρόνο.');
}

/* ===================== 14. the audit ===================== */
{
  const s = newSlide('Audit', 'Τι βρήκε ο audit — και τι απέσυρα', {dark: true});
  bullets(s, [
    ['Πραγματικά σφάλματα στο δικό μου μοντέλο, που διορθώθηκαν',
      'dirty L1 writeback που δεν διέδιδε L2 eviction · store misses που μάρκαραν dirty λάθος · '
      + 'απούσα predication στο Pin (μηδενικά REP) · placement που κοιτούσε το ΕΠΟΜΕΝΟ window.'],
    ['Ισχυρισμοί που αποσύρθηκαν',
      'Το speedup 1.505x · η εξήγηση «HWT gated από HPT» (το M5 §5.1 περιγράφει ανεξάρτητους trackers) · '
      + 'κάθε window επιλεγμένο με βάση την καμπύλη αναφοράς.'],
    ['Γιατί το λέω: ένα window που «ταιριάζει» δεν είναι απόδειξη',
      'Είναι fitted sensitivity result. Η διάκριση είναι όλη η διαφορά.'],
  ], {y: 1.45, dark: true, size: 14});
  notes(s, 'Αυτή η διαφάνεια είναι επίτηδες εδώ. Έκανα audit στο δικό μου εργαλείο και βρήκα '
    + 'πραγματικά λάθη — και απέσυρα ισχυρισμούς που δεν άντεξαν. Το πιο σημαντικό: είχα βρει '
    + 'ένα window που έφερνε τα νούμερα κοντά, αλλά αυτό είναι fitting, όχι αναπαραγωγή. '
    + 'Προτιμώ να το πω εγώ πρώτος.');
}

/* ===================== 15. what I need ===================== */
{
  const s = newSlide('Επόμενα βήματα', 'Τι χρειάζομαι για να κλείσει το κενό');
  bullets(s, [
    ['1. Το collection protocol του Figure 4 από τους συγγραφείς', 'Reset intervals, region cycling, παρονομαστής σελίδων, αν περιλαμβάνεται το setup. Έχω έτοιμο προσχέδιο επιστολής.'],
    ['2. Τα ακριβή υποσύνολα γράφων και τις εντολές προεπεξεργασίας', 'Ξέρουμε ότι είναι Twitter/Google+, όχι ποια μείωση.'],
    ['3. Άδεια SPEC CPU2017 — 4 από τις 6 υπόλοιπες μπάρες', 'Αν το εργαστήριο την έχει, είναι θέμα πρόσβασης, όχι υλοποίησης.'],
  ], {y: 1.45});
  metricRow(s, [
    {big: '0.015', label: 'PageRank, πραγματικό\nTwitter — αναπαράγεται', accent: C.blue},
    {big: '18/21', label: 'Stage 2 βήματα\n(3 multithread σε αναμονή)', accent: C.amber},
    {big: '9/14', label: 'μπάρες του Figure 4\nπου έχουν μετρηθεί', accent: C.red},
  ], {y: 3.55, h: 1.6});
  notes(s, 'Κλείνω με το τι χρειάζομαι. Το πιο χρήσιμο είναι το collection protocol — '
    + 'έχω ετοιμάσει προσχέδιο επιστολής προς τους συγγραφείς. Και η άδεια SPEC, αν την έχει '
    + 'το εργαστήριο, μου δίνει τέσσερις μπάρες αμέσως. Ευχαριστώ — ερωτήσεις;');
}

await pptx.writeFile({fileName: OUT});
console.log('wrote', OUT);
