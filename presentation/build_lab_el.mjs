/* Greek lab deck: M5 Figure 4 reproduction with a Pin tool and a cache model.
 *
 *   node presentation/build_lab_el.mjs
 *     -> presentation/CSLab_Memory_Tiering_EL.pptx
 *     -> presentation/preview/lab_el.html   (same layout, for checking and PDF export)
 *
 * Every slide is described once as positioned elements; two small back ends
 * draw it as PowerPoint and as HTML. Numbers come from result files at build
 * time (scorecard.json and the figures made by src/analysis/plot_deck_el.py).
 */
import path from 'node:path';
import {existsSync, readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {createRequire} from 'node:module';

const RUNTIME = process.env.CODEX_RUNTIME ||
  `${process.env.HOME}/.cache/codex-runtimes/codex-primary-runtime/dependencies`;
const require = createRequire(`${RUNTIME}/node/node_modules/`);
const PptxGenJS = require('pptxgenjs');

const REPO = path.resolve(import.meta.dirname, '..');
const OUT = path.join(REPO, 'presentation', 'CSLab_Memory_Tiering_EL.pptx');
const PREVIEW = path.join(REPO, 'presentation', 'preview', 'lab_el.html');
const W = 10, H = 5.625;

const C = {ink: '1A1C1E', grey: '5E6266', light: 'A7ABAF', rule: 'DDDFE1', blue: '1D5C63',
  blueBg: 'EAF1F1', paper: 'F4F4F2', white: 'FFFFFF', orange: 'D9822B', hlRow: 'EFF4F4'};
const FONT = 'Noto Sans', SERIF = 'Noto Serif', MONO = 'DejaVu Sans Mono';

/* sections for the running strip at the top of each slide (replaces per-slide labels) */
const SECTIONS = [
  ['Εισαγωγή', ['Το ερώτημα', 'Η πρόκληση']],
  ['Pintool & μοντέλο cache', ['Το pintool', 'Το μοντέλο cache', 'Βαθμονόμηση']],
  ['Αποτελέσματα', ['Κύριο αποτέλεσμα', 'Η συμβολή του μοντέλου cache', 'Πώς φτάσαμε εδώ', 'Window μέτρησης']],
  ['SimCXL', ['Τα όρια του Pin', 'SimCXL · full-system CXL', 'SimCXL · αποτελέσματα']],
  ['Trackers & KV', ['Οι trackers του M5', 'Πέρα από τα GAP']],
  ['Υποδομή', ['Υποδομή και αναπαραγωγιμότητα']],
  ['Αναλυτικά αποτελέσματα', ['Λεπτομέρειες']],
  ['Μελλοντικά βήματα', ['Επόμενα βήματα']],
];

/* ---------- data read at build time ---------- */
const CARD = JSON.parse(readFileSync(path.join(REPO, 'results/prefetch-ladder-2026-11-15/scorecard.json'), 'utf8'));
const WL = ['bfs', 'cc', 'sssp', 'bc', 'pr', 'tc'];
const NAME = {bfs: 'BFS', cc: 'CC', sssp: 'SSSP', bc: 'BC', pr: 'PR', tc: 'TC'};
const mean = k => WL.reduce((t, w) => t + CARD[w][k], 0) / WL.length;
const f2 = v => v.toFixed(2);
const MEAN_NEW = f2(mean('loo_error')), MEAN_OLD = f2(mean('old_epoch'));
// main Figure-4 slide shows these four (same list as MAIN in plot_deck_el.py)
const MAIN = ['bfs', 'cc', 'pr', 'tc'];
const meanOf = (ws, k) => ws.reduce((t, w) => t + CARD[w][k], 0) / ws.length;
const MAIN_NEW = f2(meanOf(MAIN, 'loo_error')), MAIN_OLD = f2(meanOf(MAIN, 'old_epoch'));
const T_LO = Math.round(Math.min(...WL.map(w => CARD[w].loo_instructions)) / 1e9);
const T_HI = Math.round(Math.max(...WL.map(w => CARD[w].loo_instructions)) / 1e9);
const gr = n => n.toLocaleString('el-GR');

/* ---------- element constructors ---------- */
const T = (x, y, w, h, content, o = {}) => ({k: 'text', x, y, w, h, content, o});
const R = (x, y, w, h, o = {}) => ({k: 'rect', x, y, w, h, o});
const L = (x1, y1, x2, y2, o = {}) => ({k: 'line', x1, y1, x2, y2, o});
function I(rel, box, align = 'center') {
  const p = path.join(REPO, rel);
  const b = readFileSync(p);
  const iw = b.readUInt32BE(16), ih = b.readUInt32BE(20);
  const s = Math.min(box.w / iw, box.h / ih), w = iw * s, h = ih * s;
  const x = align === 'left' ? box.x : box.x + (box.w - w) / 2;
  return {k: 'image', p, x, y: box.y + (box.h - h) / 2, w, h};
}
/* paragraphs: [[run, run], ...]; run = string | {t, b, c, i, f} */
const P = (...paras) => paras.map(p => (Array.isArray(p) ? p : [p]));
const b = t => ({t, b: true});
const blue = t => ({t, b: true, c: C.blue});
const mono = t => ({t, f: MONO});

/* table drawn with rules, the same in both back ends */
function table(x, y, colW, rows, {size = 11, rowH = 0.34, head = true, align = [], hl = -1} = {}) {
  const els = [];
  rows.forEach((r, ri) => {
    const yy = y + ri * rowH;
    if (ri === hl) els.push(R(x, yy, colW.reduce((a, c) => a + c, 0), rowH, {fill: C.hlRow}));
    let xx = x;
    r.forEach((cell, ci) => {
      const isHead = head && ri === 0;
      els.push(T(xx + 0.06, yy, colW[ci] - 0.12, rowH, P([isHead ? cell : (ri === hl ? b(cell) : cell)]),
        {size: isHead ? size - 1.5 : size, color: isHead ? C.grey : (ri === hl ? C.blue : C.ink),
         bold: isHead, align: align[ci] || 'left', valign: 'middle'}));
      xx += colW[ci];
    });
    const tw = colW.reduce((a, c) => a + c, 0);
    if (ri === 0) els.push(L(x, yy, x + tw, yy, {color: C.ink, w: 1.25}));
    if (ri === 0 && head) els.push(L(x, yy + rowH, x + tw, yy + rowH, {color: C.ink, w: 0.6}));
    if (ri === rows.length - 1) els.push(L(x, yy + rowH, x + tw, yy + rowH, {color: C.ink, w: 1.25}));
  });
  return els;
}

/* ---------- slides ---------- */
const slides = [];
const add = s => slides.push(s);
const body = (x, y, w, h, paras, o = {}) => T(x, y, w, h, paras, {size: 13, color: C.ink, psa: 9, ...o});

/* 1. title */
add({title: null, notes:
  'Καλημέρα. Θα σας παρουσιάσω την αναπαραγωγή του Figure 4 του M5, από το ASPLOS 2025, σε έναν απλό desktop υπολογιστή. '
  + 'Το M5 χρησιμοποίησε ειδικό υλικό, ένα FPGA πάνω σε CXL controller. Εγώ έφτιαξα ένα pintool με μοντέλο της ιεραρχίας cache '
  + 'που μετρά το ίδιο μέγεθος σε software. Το κύριο αποτέλεσμα: στα έξι GAP workloads του paper, το μέσο μέγιστο σφάλμα '
  + `είναι ${MEAN_NEW}. Μετά θα δείξω τη μεταφορά του ίδιου μετρητή σε full-system CXL προσομοιωτή και την υπόλοιπη δουλειά πάνω στο M5.`,
  els: [
    T(0.9, 1.2, 8.4, 0.3, P(['Advanced Computer Architecture  ·  ΕΜΠ / CSLab']), {size: 11, color: C.grey}),
    T(0.9, 1.55, 8.6, 1.1, P(['Sub-page hot skewness σε CXL tiered memory']), {size: 30, bold: true, color: C.ink, lh: 1.05, font: SERIF}),
    L(0.9, 2.8, 1.9, 2.8, {color: C.blue, w: 2}),
    T(0.9, 2.98, 8.2, 0.9, P(['Αναπαραγωγή του Figure 4 του M5 (ASPLOS \'25) με δικό μας pintool και μοντέλο cache, σε έναν desktop υπολογιστή']),
      {size: 15, color: C.grey, lh: 1.25}),
    L(0.9, 4.05, 9.2, 4.05, {color: C.rule}),
    T(0.9, 4.2, 5, 0.32, P(['Ιάσων Ζακυνθινός']), {size: 13, bold: true, color: C.ink}),
    T(0.9, 4.52, 5, 0.3, P(['Νοέμβριος 2026']), {size: 11, color: C.grey}),
    T(5.4, 4.2, 3.8, 0.62, P([{t: 'μέσο max σφάλμα έναντι M5', c: C.grey}], [blue(`${MEAN_NEW}  σε 6 GAP workloads`)]),
      {size: 11, align: 'right'}),
  ]});

/* 2. the question */
{
  const els = [
    body(0.6, 1.4, 4.7, 3.7, P(
      ['Σε CXL tiered memory το λειτουργικό μεταφέρει ', b('ολόκληρες σελίδες 4 KB'), ' ανάμεσα σε τοπική DRAM και CXL μνήμη. Αν μια «hot» σελίδα χρησιμοποιεί λίγα cache lines, το μεγαλύτερο μέρος της μεταφοράς δεν χρειαζόταν.'],
      ['Το M5 βάζει μετρητές ', b('μέσα στον CXL controller'), ' (FPGA Agilex 7): PAC ανά σελίδα, WAC ανά 64 B word, και τους bounded trackers HPT / HWT.'],
      [b('Figure 4:'), ' για κάθε workload, η πιθανότητα μια σελίδα να έχει το πολύ N από τα 64 words της προσπελασμένα, για N = 4, 8, 16, 32, 48.'],
    ), {size: 13}),
  ];
  // schematic: CPU -> LLC -> CXL link -> controller (PAC/WAC) -> DRAM
  const bx = 5.75, bw = 3.65;
  const boxes = [['CPU cores', 'L1 / L2'], ['LLC', 'shared'], ['CXL controller', 'PAC · WAC · HPT · HWT'], ['DRAM στη συσκευή', '']];
  boxes.forEach(([a, c], i) => {
    const y = 1.45 + i * 0.86, hl = i === 2;
    els.push(R(bx, y, bw, 0.58, {fill: hl ? C.blueBg : C.white, line: hl ? C.blue : C.light, lw: hl ? 1.25 : 0.75}));
    els.push(T(bx + 0.15, y + 0.05, bw - 0.3, 0.26, P([a]), {size: 12, bold: true, color: hl ? C.blue : C.ink}));
    if (c) els.push(T(bx + 0.15, y + 0.3, bw - 0.3, 0.24, P([c]), {size: 10, color: C.grey}));
    if (i < 3) els.push(L(bx + bw / 2, y + 0.58, bx + bw / 2, y + 0.86, {color: C.light, arrow: true}));
  });
  els.push(T(bx + bw / 2 + 0.1, 1.45 + 1.5 * 0.86 + 0.13, 1.6, 0.22, P(['CXL link: LLC misses']), {size: 9, color: C.grey}));
  els.push(T(bx, 4.9, bw, 0.25, P(['Ο μετρητής βλέπει ό,τι φτάνει στη συσκευή.']), {size: 9.5, color: C.grey, i: true}));
  add({kicker: 'Το ερώτημα', title: 'Πόσα από τα 64 words μιας σελίδας 4 KB χρησιμοποιούνται πραγματικά;', els, notes:
    'Το πλαίσιο. Σε συστήματα με CXL μνήμη, το λειτουργικό κρατά τις «ζεστές» σελίδες στην τοπική DRAM και μεταφέρει σελίδες των 4 KB. '
    + 'Αν μια ζεστή σελίδα χρησιμοποιεί μόνο λίγα cache lines, μεταφέρουμε άχρηστα δεδομένα. Το M5 το μέτρησε με μετρητές μέσα στον CXL controller, '
    + 'που βλέπουν κάθε request που φτάνει στη μνήμη. Το Figure 4 είναι η κατανομή: τι ποσοστό σελίδων έχουν το πολύ 4, 8, 16, 32 ή 48 '
    + 'από τα 64 words τους προσπελασμένα. Το κρίσιμο σημείο για τη συνέχεια: ο μετρητής βλέπει ό,τι φτάνει στη συσκευή, όχι ό,τι εκτελεί ο επεξεργαστής.'});
}

/* 3. the challenge */
add({kicker: 'Η πρόκληση', title: 'Η ίδια μέτρηση, χωρίς FPGA και χωρίς συσκευή CXL', notes:
  'Το testbed του M5 είναι δύο Xeon Sapphire Rapids, ένα FPGA Agilex 7 και τρεις τροποποιημένοι kernels. Εδώ έχουμε έναν i9-12900K. '
  + 'Η ιδέα: οι μετρητές του M5 είναι απλή λογική — μάσκες και counters ανά σελίδα — άρα μπορούν να γίνουν software. Το δύσκολο είναι να τους '
  + 'τροφοδοτήσεις με τη σωστή ροή, δηλαδή με αυτό που θα έφτανε στη συσκευή. Αυτό κάνει το μοντέλο cache. '
  + 'Μια λεπτομέρεια που βρήκαμε διαβάζοντας το artifact: ο Table 3 γράφει 10 ways LLC, αλλά η μάσκα CAT που προγραμματίζει το script, 0x7FC0, έχει 9 bits. '
  + 'Τρέξαμε και τις δύο διαμορφώσεις.',
  els: [
    ...table(0.6, 1.4, [2.0, 3.35, 3.45], [
      ['', 'M5 (ASPLOS \'25)', {t: 'Αυτή η εργασία', b: true, c: C.blue}],
      ['Πλατφόρμα', '2× Xeon Gold 6430 (Sapphire Rapids)', '1× i9-12900K, 32 GB RAM'],
      ['Μετρητές', 'PAC / WAC σε FPGA Agilex 7', 'PAC / WAC σε software, μέσα στο pintool'],
      ['Ροή που μετράται', 'requests στο CXL link', 'misses από μοντέλο cache του SPR'],
      ['LLC', '60 MB, CAT: 10 από 15 ways (= 40 MB)', 'μοντέλο 40 MB / 10 ways (και 9 ways)'],
      ['Kernel', '3 τροποποιημένοι kernels', 'κανένας: μέτρηση σε user space'],
      ['Workloads', 'GAPBS σε Twitter, Google+', 'ίδια datasets, εντολές του artifact'],
    ], {size: 11.5, rowH: 0.42}),
    R(0.6, 4.55, 8.8, 0.55, {fill: C.paper}),
    T(0.8, 4.55, 8.4, 0.55, P([b('Από το artifact: '), 'ο Table 3 γράφει 10 LLC ways, η μάσκα CAT του script (', mono('0x7FC0'), ') έχει 9 bits. Μετρήσαμε και τα δύο.']),
      {size: 11, color: C.ink, valign: 'middle'}),
  ]});

/* 4. pintool pipeline */
{
  const els = [];
  const stages = [
    ['Pin', 'κάθε load / store', false],
    ['L1d', '48 KB · 12-way', false],
    ['L2', '2 MB · 16-way\n+ prefetchers', true],
    ['LLC', '40 MB · 10-way\nshared', false],
    ['Προς CXL', 'misses · prefetches\nwritebacks', true],
    ['PAC / WAC', 'ακριβείς μετρητές\n→ Figure 4', true],
  ];
  const x0 = 0.6, bw = 1.3, gap = 0.2, y = 1.5, h = 1.05;
  stages.forEach(([a, c, hl], i) => {
    const x = x0 + i * (bw + gap);
    els.push(R(x, y, bw, h, {fill: hl ? C.blueBg : C.white, line: hl ? C.blue : C.light, lw: hl ? 1.25 : 0.75}));
    els.push(T(x + 0.1, y + 0.08, bw - 0.2, 0.28, P([a]), {size: 12, bold: true, color: hl ? C.blue : C.ink}));
    els.push(T(x + 0.1, y + 0.4, bw - 0.2, 0.6, P(...c.split('\n').map(t => [t])), {size: 9.5, color: C.grey, psa: 0}));
    if (i < stages.length - 1) els.push(L(x + bw + 0.02, y + h / 2, x + bw + gap - 0.02, y + h / 2, {color: C.grey, arrow: true}));
  });
  els.push(L(2.1, 2.6, 2.1, 2.7, {color: C.light}), L(2.1, 2.7, 6.4, 2.7, {color: C.light}), L(6.4, 2.6, 6.4, 2.7, {color: C.light}));
  els.push(T(2.1, 2.74, 4.3, 0.25, P(['μοντέλο ιεραρχίας cache του Sapphire Rapids (testbed του M5)']), {size: 9.5, color: C.grey, align: 'center'}));
  els.push(body(0.6, 3.1, 4.25, 2.1, P(
    [b('Γιατί: '), 'ένας απλός Pin tracer βλέπει κάθε προσπέλαση πριν την απορροφήσουν οι caches.'],
    [b('Ένα πέρασμα, τρεις ροές: '), 'accesses, misses και traffic, στο ίδιο window και στις ίδιες σελίδες.'],
  ), {size: 11.5, psa: 7}));
  els.push(body(5.15, 3.1, 4.25, 2.1, P(
    [b('Virtual διευθύνσεις, ακριβώς: '), 'VA[11:0] = PA[11:0], άρα η θέση ενός word μέσα στη σελίδα δεν αλλάζει από το translation.'],
  ), {size: 11.5, psa: 7}));
  add({kicker: 'Το pintool', title: 'Το pintool ξαναχτίζει την ιεραρχία cache και μετρά ό,τι θα έβλεπε η συσκευή CXL', els, notes:
    'Αυτή είναι η καρδιά του εργαλείου. Το Pin μας δίνει κάθε load και store του προγράμματος. Αν μετρούσαμε αυτά απευθείας, θα μετρούσαμε λάθος πράγμα, '
    + 'γιατί οι caches απορροφούν ακριβώς την κίνηση με μεγάλη επαναχρησιμοποίηση. Γι\' αυτό κάθε προσπέλαση περνά από μοντέλο L1, L2 και LLC με τη γεωμετρία '
    + 'του Sapphire Rapids του M5, και μόνο ό,τι βγαίνει από το LLC — misses, prefetches και dirty writebacks — φτάνει στους μετρητές PAC/WAC. '
    + 'Στο ίδιο πέρασμα κρατάμε και τις τρεις ροές, ώστε να συγκρίνουμε με ακρίβεια τι προσθέτει το μοντέλο. '
    + 'Οι virtual διευθύνσεις δεν είναι προσέγγιση εδώ: τα 12 χαμηλά bits είναι ίδια σε virtual και physical, άρα το word μέσα στη σελίδα είναι ακριβές.'});
}

/* 5. cache model */
add({kicker: 'Το μοντέλο cache', title: 'Γεωμετρία από το testbed του M5, prefetchers από το manual της Intel', notes:
  'Οι λεπτομέρειες του μοντέλου. Οι διαστάσεις είναι του Sapphire Rapids που χρησιμοποίησε το M5: 48 KB L1d, 2 MB L2, και LLC περιορισμένο με CAT όπως στο artifact. '
  + 'Write-back, write-allocate, true LRU, και τα dirty writebacks μετρώνται, γιατί κι αυτά φτάνουν στη συσκευή. '
  + 'Το σημαντικό νέο κομμάτι είναι οι hardware prefetchers. Για τη συσκευή CXL ένα prefetch είναι read σαν όλα τα άλλα, άρα αγγίζει words. '
  + 'Μοντελοποιήσαμε τους δύο L2 prefetchers που τεκμηριώνει η Intel, με όλες τις σταθερές από το Optimization Manual: τον spatial, που συμπληρώνει το ζευγάρι 128 bytes, '
  + 'και τον streamer, με 32 streams, δύο prefetches ανά lookup, έως 20 lines μπροστά και ποτέ έξω από τη σελίδα. '
  + 'Μία μόνο τιμή δεν δίνεται από την Intel — πόσες διαδοχικές προσπελάσεις επιβεβαιώνουν ένα stream. Τη δοκιμάσαμε με 1 και 2: το CC αλλάζει από 0.243 σε 0.234, άρα δεν επηρεάζει το συμπέρασμα.',
  els: [
    ...table(0.6, 1.4, [0.8, 0.95, 0.85, 1.95], [
      ['Επίπεδο', 'Μέγεθος', 'Ways', 'Ρόλος'],
      ['L1d', '48 KB', '12', 'private ανά thread'],
      ['L2', '2 MB', '16', 'private + prefetchers'],
      ['LLC', '40 MB', '10', 'shared, CAT partition'],
    ], {size: 11.5, rowH: 0.4}),
    body(0.6, 3.15, 4.4, 2.0, P(
      ['Write-back, write-allocate, ', b('true LRU'), '.'],
      ['Τα dirty writebacks μετρώνται: φτάνουν κι αυτά στη συσκευή.'],
      ['LLC: 10 ways όπως ο Table 3 του M5 (και έλεγχος με 9).'],
    ), {size: 11.5, psa: 6}),
    R(5.35, 1.4, 4.05, 3.75, {fill: C.paper}),
    T(5.55, 1.52, 3.7, 0.3, P(['Hardware prefetchers (L2)']), {size: 12.5, bold: true, color: C.blue}),
    body(5.55, 1.9, 3.7, 3.2, P(
      [b('Spatial: '), 'σε κάθε L2 miss φέρνει και το ζευγάρι line του 128 B chunk.'],
      [b('Streamer: '), '32 streams, ένα ανά σελίδα 4 KB · 2 prefetches ανά lookup · έως 20 lines μπροστά · ποτέ έξω από τη σελίδα.'],
      ['Για τη συσκευή CXL ένα prefetch είναι read όπως κάθε άλλο: ', b('αγγίζει words.')],
    ), {size: 11, psa: 7}),
  ]});

/* 6. calibration */
add({kicker: 'Βαθμονόμηση', title: 'Πριν από κάθε αποτέλεσμα, το εργαλείο δίνει την αναλυτική απάντηση', notes:
  'Πριν εμπιστευτούμε οποιονδήποτε αριθμό, ελέγχουμε το όργανο σε μοτίβα με γνωστή απάντηση. Ένα sweep με stride 4096 bytes πρέπει να αγγίζει ακριβώς ένα word ανά σελίδα, '
  + 'με stride 64 bytes και τα 64. Το εργαλείο δίνει 1, 3.999, 15.996 και 63.981 — η μικρή απόκλιση είναι οι σελίδες στα άκρα του buffer. '
  + 'Το ίδιο ισχύει για τα νέα κομμάτια: το window ladder ελέγχεται απέναντι σε brute-force υπολογισμό και ο prefetcher απέναντι στους κανόνες της Intel. '
  + 'Και κάθε run γράφει manifest με τα hashes του εργαλείου, του εκτελέσιμου και του input, ώστε να ξέρουμε ακριβώς τι μετρήθηκε.',
  els: [
    I('docs/assets/deck/calibration.png', {x: 0.5, y: 1.35, w: 5.2, h: 3.8}),
    body(6.0, 1.5, 3.45, 3.6, P(
      [b('Γνωστά μοτίβα: '), 'stride 4096 → 64 B πρέπει να δώσει 1, 4, 16, 64 words ανά σελίδα.'],
      ['Μέτρηση: ', b('1 · 3.999 · 15.996 · 63.981'), '.'],
      [b('Κάθε run αφήνει ίχνος. '), 'Κρατάμε την εντολή και τα hashes του εργαλείου, του προγράμματος και του input, ώστε για κάθε αριθμό να ξέρουμε από πού βγήκε.'],
    ), {size: 11.5, psa: 8}),
  ]});

/* 7. main result */
add({kicker: 'Κύριο αποτέλεσμα', title: `Το Figure 4 του M5 σε desktop: μέσο max σφάλμα ${MAIN_NEW}`, notes:
  'Αυτό είναι το κύριο αποτέλεσμα, στη μορφή του Figure 4. Πάνω το M5 όπως δημοσιεύτηκε. Στη μέση, οι προσπελάσεις της εφαρμογής όπως τις βλέπει ένας απλός Pin tracer. '
  + 'Κάτω, η ροή προς τη συσκευή CXL από το pintool με το μοντέλο cache — αυτή συγκρίνεται με το M5. '
  + 'Πάνω από κάθε ομάδα είναι το μέγιστο σφάλμα στα πέντε σημεία N. BFS 0.08, TC 0.06, PR 0.02: οι μπάρες ουσιαστικά ταυτίζονται. '
  + 'Το PR έχει πυκνές σελίδες και στις δύο πλευρές. Το CC, 0.24, είναι το workload με το μεγαλύτερο περιθώριο, στο N=48. '
  + 'Τα inputs είναι τα πραγματικά datasets που ονομάζει το artifact, Twitter και Google+, με τις εντολές του artifact. '
  + 'Όλη η καμπάνια είναι 1,74 τρισεκατομμύρια instructions κάτω από Pin.',
  els: [
    I('docs/assets/deck/fig4_main.png', {x: 0.3, y: 1.28, w: 7.45, h: 4.0}),
    T(7.85, 1.4, 1.65, 0.75, P([blue(MAIN_NEW)]), {size: 40, lh: 1}),
    T(7.85, 2.15, 1.65, 0.5, P(['μέσο max σφάλμα'], ['αρχικό μοντέλο: ' + MAIN_OLD]), {size: 10, color: C.grey, psa: 0}),
    L(7.85, 2.8, 9.45, 2.8, {color: C.rule}),
    body(7.85, 2.92, 1.62, 2.35, P(
      [b('Inputs: '), 'Twitter (WWW \'10), Google+ (IMC \'12), όπως ονομάζει το artifact.'],
      [b('Εντολές: '), 'του artifact (π.χ. BFS 200 trials).'],
      [b('Κλίμακα: '), '1,74 τρισ. instructions υπό Pin.'],
    ), {size: 9.5, psa: 5}),
  ]});

/* 8. what the cache model contributes */
{
  add({kicker: 'Η συμβολή του μοντέλου cache', title: 'Χωρίς το μοντέλο cache, το σφάλμα υπερδιπλασιάζεται', notes:
    'Εδώ φαίνεται γιατί άξιζε το μοντέλο cache. Ίδια εκτέλεση, ίδιο window, ίδιες σελίδες· αλλάζει μόνο το τι μετράμε. Γκρι: οι προσπελάσεις της εφαρμογής, '
    + 'αυτό που θα έδινε ένας απλός Pin tracer. Μπλε: ό,τι φτάνει στη μνήμη μέσα από το μοντέλο. Στα BFS, CC και TC το σφάλμα πέφτει δραματικά — '
    + 'στο BFS από 0.35 σε 0.08, στο TC από 0.34 σε 0.06. Στα SSSP, BC και PR οι σελίδες είναι πυκνές και στις δύο ροές, όπως και στο M5. '
    + 'Ο μέσος όρος πέφτει από 0.25 σε 0.11. Αυτό επιβεβαιώνει την υπόθεση του M5 ότι το σωστό μέγεθος είναι η ροή στη συσκευή.',
    els: [
      I('docs/assets/deck/cache_value.png', {x: 0.4, y: 1.3, w: 5.9, h: 3.95}),
      body(6.6, 1.5, 2.85, 3.7, P(
        ['Ίδια εκτέλεση, ίδιο window, ίδιες σελίδες: αλλάζει μόνο ', b('τι μετράμε'), '.'],
        [b('BFS'), ' 0.35 → 0.08', ' ', b('TC'), ' 0.34 → 0.06', ' ', b('CC'), ' 0.53 → 0.24'],
        ['Στα SSSP, BC, PR οι σελίδες είναι πυκνές και στις δύο ροές — όπως και στο M5.'],
        [{t: 'Μέσος όρος: 0.25 → 0.11.', b: true, c: C.blue}],
      ), {size: 12, psa: 10}),
    ]});
}

/* 9. two mechanisms on the artifact inputs */
add({kicker: 'Πώς φτάσαμε εδώ', title: `Δύο μηχανισμοί, πάνω στα datasets του artifact: ${MEAN_OLD} → ${MEAN_NEW}`, notes:
  'Η πορεία. Η βάση είναι τα inputs: το artifact ονομάζει Twitter και Google+, όχι συνθετικούς γράφους· τα κατεβάσαμε και τρέξαμε τις εντολές του artifact. '
  + 'Με το αρχικό μοντέλο — μόνο demand misses, window 10 εκατομμυρίων events — το μέσο σφάλμα ήταν 0.50. Δύο μηχανισμοί μας έφεραν στο 0.11. '
  + 'Πρώτος, το hardware prefetching: το CC πέφτει από 0.49 σε 0.24 και δεν εξαρτάται πια από το window. '
  + 'Δεύτερος, το window μέτρησης. Η κάλυψη words μόνο αυξάνεται όσο μεγαλώνει το window, και το M5 δεν δημοσιεύει το δικό του. '
  + 'Με ένα run κρατάμε όλα τα μήκη (window ladder). Αν το κοινό window οριστεί σε events, κάθε workload παίρνει άλλο χρονικό διάστημα, '
  + `γιατί διαφέρουν περίπου 300 φορές σε κίνηση ανά instruction: μέσος ${f2(mean('ev_loo_error'))}. Σε instructions, δηλαδή σε χρόνο, όπως δειγματοληπτεί ένας profiler: ${MEAN_NEW}. `
  + `Το μήκος για κάθε workload το διαλέγουν τα άλλα πέντε, και βγαίνει κάθε φορά ${T_LO} με ${T_HI} δισεκατομμύρια instructions. `
  + 'Κανένα βήμα δεν είναι προσαρμογή στην καμπύλη του M5 ανά workload.',
  els: [
    I('docs/assets/deck/progress.png', {x: 0.4, y: 1.3, w: 5.9, h: 3.95}),
    ...[['0', 'Datasets του artifact', 'Twitter (WWW \'10) και Google+ (IMC \'12), με τις εντολές του artifact.'],
      ['1', 'Hardware prefetching', 'CC: 0.49 → 0.24, ανεξάρτητα από το window.'],
      ['2', 'Κοινό window σε χρόνο', `Ίδιο χρονικό διάστημα για όλα τα workloads, μετρημένο σε instructions αντί για events: ${f2(mean('ev_loo_error'))}\u00a0→\u00a0${MEAN_NEW}.`]].flatMap(([n, h, t], i) => {
      const y = 1.5 + i * 1.22;
      return [T(6.6, y, 0.45, 0.45, P([n]), {size: 22, bold: true, color: i ? C.blue : C.light}),
        T(7.1, y + 0.02, 2.4, 0.3, P([h]), {size: 12.5, bold: true, color: C.ink}),
        T(7.1, y + 0.36, 2.35, 0.75, P([t]), {size: 10.5, color: C.grey})];
    }),
  ]});

/* 10. kernel traffic */
add({kicker: 'Τα όρια του Pin', title: 'Ό,τι αντιγράφει ο kernel, το Pin δεν το βλέπει', notes:
  'Ένα όριο της μεθόδου, που το μετρήσαμε. Το Pin βλέπει μόνο τις εντολές του ίδιου του προγράμματος. Όταν το πρόγραμμα διαβάζει ένα αρχείο, '
  + 'την αντιγραφή στη μνήμη την κάνει ο kernel, και αυτή το Pin δεν τη βλέπει. Η συσκευή CXL όμως τη βλέπει: γι\' αυτήν ένα write είναι write, όποιος κι αν το έστειλε. '
  + 'Το δείξαμε με ένα μικρό πείραμα: φέρνουμε 512 MiB στη μνήμη με δύο τρόπους. Με read την αντιγραφή την κάνει ο kernel, και το Pin βλέπει πέντε προσπελάσεις. '
  + 'Με memcpy την κάνει το πρόγραμμα, και το Pin βλέπει περίπου 25 εκατομμύρια, σε 262 χιλιάδες σελίδες, όλες πλήρως πυκνές. '
  + 'Το GAPBS φορτώνει τον γράφο με read. Στο κύριο αποτέλεσμα αυτό δεν παίζει ρόλο, γιατί μετράμε μόνο τον υπολογισμό, μετά το φόρτωμα. '
  + 'Για να δούμε όμως ό,τι βλέπει πραγματικά η συσκευή, πρέπει να μετρήσουμε στην ίδια τη συσκευή — αυτό κάνει το επόμενο κομμάτι, με τον προσομοιωτή.',
  els: [
    body(0.6, 1.45, 3.95, 2.4, P(
      ['Το Pin παρακολουθεί μόνο τις εντολές του ίδιου του προγράμματος.'],
      ['Όταν το πρόγραμμα διαβάζει ένα αρχείο με ', mono('read()'), ', την αντιγραφή στη μνήμη την κάνει ο ', b('kernel'), ' — και αυτήν το Pin δεν τη βλέπει.'],
      ['Η συσκευή CXL τη βλέπει κανονικά: για τη μνήμη ένα write είναι write, όποιος κι αν το έστειλε.'],
    ), {size: 12.5, psa: 9}),
    T(4.95, 1.45, 4.45, 0.3, P(['Πείραμα: φέρνουμε 512 MiB στη μνήμη με δύο τρόπους']), {size: 11, bold: true, color: C.grey}),
    ...table(4.95, 1.82, [1.75, 2.7], [
      ['Ποιος αντιγράφει', 'Τι βλέπει το Pin'],
      [{t: 'read(): ο kernel', b: true}, '5 προσπελάσεις, σε 4 σελίδες'],
      [{t: 'memcpy(): το πρόγραμμα', b: true}, '≈ 25 εκατ. προσπελάσεις, σε 262 χιλ. σελίδες, όλες πλήρως πυκνές'],
    ], {size: 11.5, rowH: 0.62, align: ['left', 'left']}),
    R(0.6, 4.05, 4.15, 1.05, {fill: C.paper}),
    T(0.8, 4.05, 3.85, 1.05, P(['Το GAPBS φορτώνει τον γράφο με ', mono('read()'), '. Στο κύριο αποτέλεσμα δεν επηρεάζει: μετράμε μόνο τον υπολογισμό, μετά το φόρτωμα.']),
      {size: 11, color: C.ink, valign: 'middle'}),
    R(5.15, 4.05, 4.25, 1.05, {fill: C.blueBg}),
    T(5.35, 4.05, 3.95, 1.05, P(['Για να δούμε ό,τι βλέπει η συσκευή, μετράμε ', b('στην ίδια τη συσκευή'), ': σε full-system προσομοιωτή, όπου φαίνονται και ο kernel και οι φυσικές διευθύνσεις.']),
      {size: 11, color: C.ink, valign: 'middle'}),
  ]});

/* 11. SimCXL port */
add({kicker: 'SimCXL · full-system CXL', title: 'Ο ίδιος μετρητής, μέσα σε έναν full-system CXL προσομοιωτή', notes:
  'Το δεύτερο σκέλος. Ένας full-system προσομοιωτής τρέχει ολόκληρο σύστημα — λειτουργικό, kernel και εφαρμογή — πάνω σε προσομοιωμένο υλικό, με μια συσκευή μνήμης CXL. '
  + 'Ο στόχος του ευρύτερου project είναι το CXLRAMSim, που δεν έχει δημοσιευτεί ακόμα, οπότε χρησιμοποιήσαμε το SimCXL, γνωστό και ως CXL-DMSim, πάνω σε gem5. '
  + 'Τον μετρητή του pintool τον βάλαμε αυτούσιο στην είσοδο της συσκευής, τη CXL bridge, εκεί όπου το M5 έχει τον controller του. '
  + 'Εκεί κάθε request φτάνει με τη φυσική του διεύθυνση, είτε το έστειλε το πρόγραμμα είτε ο kernel — αυτό που έλειπε από το Pin. '
  + 'Πριν από οτιδήποτε άλλο τον ελέγξαμε: σε ένα γραμμικό sweep κάθε line πρέπει να φτάσει στη συσκευή ακριβώς μία φορά, 30.321 requests για 30.321 lines. '
  + 'Η πρώτη εκδοχή μετρούσε 87.558. Όταν η ουρά της συσκευής είναι γεμάτη, το request απορρίπτεται και ξαναστέλνεται, και εμείς το μετρούσαμε κάθε φορά. '
  + 'Το ιστόγραμμα words ανά σελίδα έμενε σωστό, οπότε χωρίς αυτόν τον έλεγχο δεν θα το βλέπαμε. Το hook μπήκε μετά τον έλεγχο του retry. '
  + 'Μετρήσαμε και στον memory controller πίσω από τη bridge: ίδια ιστογράμματα.',
  els: [
    body(0.6, 1.45, 4.5, 2.4, P(
      ['Ο προσομοιωτής τρέχει ', b('ολόκληρο σύστημα'), ' — λειτουργικό, kernel και εφαρμογή — με μια προσομοιωμένη συσκευή μνήμης CXL.'],
      ['Το CXLRAMSim δεν έχει δημοσιευτεί ακόμα, οπότε χρησιμοποιήσαμε το SimCXL (CXL-DMSim, πάνω σε gem5).'],
      ['Ο μετρητής μπήκε αυτούσιος στην ', b('είσοδο της συσκευής'), ': εκεί φτάνει κάθε request με φυσική διεύθυνση, είτε από το πρόγραμμα είτε από τον kernel.'],
    ), {size: 12, psa: 8}),
    R(5.5, 1.45, 3.95, 1.75, {fill: C.paper}),
    T(5.7, 1.55, 3.6, 1.6, P(
      [mono('if (!retryReq) {')],
      [mono('  if (bridge.hotskewEnabled)')],
      [mono('    bridge.hotskewProbe')],
      [mono('      .onRequest(pkt->getAddr(),')],
      [mono('                 pkt->isWrite());')],
    ), {size: 10, color: C.ink, psa: 0, lh: 1.15}),
    T(5.5, 3.3, 3.95, 0.3, P(['μία κλήση ανά request, στην είσοδο της συσκευής']), {size: 9.5, color: C.grey, i: true}),
    R(0.6, 4.15, 8.85, 1.0, {fill: C.blueBg}),
    T(0.8, 4.15, 8.5, 1.0, P(
      [b('Πρώτα ο έλεγχος. '), 'Σε ένα γραμμικό sweep κάθε line πρέπει να φτάσει μία φορά: 30.321 requests για 30.321 lines. Η πρώτη εκδοχή μετρούσε 87.558 — '
        + 'όταν η ουρά της συσκευής γεμίζει, το request ξαναστέλνεται, και το μετρούσαμε κάθε φορά. Το hook μπήκε μετά τον έλεγχο του retry.'],
    ), {size: 11, color: C.ink, valign: 'middle'}),
  ]});

/* 12. SimCXL results */
add({kicker: 'SimCXL · αποτελέσματα', title: 'Το Figure 4 σε full-system προσομοίωση: PR 0.02, BFS 0.12, CC 0.17', notes:
  'Τα αποτελέσματα του προσομοιωτή, στην ίδια μορφή. Εδώ μετράμε στη θύρα της CXL bridge, με φυσικές διευθύνσεις και τον kernel ορατό. '
  + 'Τα inputs είναι συνθετικοί γράφοι Kronecker, γιατί ο προσομοιωτής είναι πολύ πιο αργός: το PageRank χρειάστηκε 16,6 ώρες για 1,47 δισεκατομμύρια requests, το TC 31 ώρες. '
  + 'Χωρίς κανένα μοντέλο prefetch ή επιλογή window, το PR βγαίνει 0.02, το BFS 0.12 και το CC 0.17. Το TC, 0.38, βγαίνει πιο πυκνό από το M5 σε αυτό το input. '
  + 'Για τέτοια runs χρειάστηκε checkpoint/restore: χρησιμοποιούμε DMTCP, επικυρωμένο ώστε το restored run να δίνει byte-for-byte τα ίδια αποτελέσματα. Το Liblinear τρέχει τώρα με αυτόν τον μηχανισμό.',
  els: [
    I('docs/assets/deck/sim.png', {x: 0.4, y: 1.3, w: 9.2, h: 3.25}),
    ...[['1,47 δισ.', 'requests στη bridge (PR)'], ['62 ώρες', 'full-system προσομοίωσης'],
      ['byte-for-byte', 'checkpoint / restore (DMTCP)'], ['Kronecker', 'inputs · 10M-event windows']].flatMap(([a, c], i) => {
      const x = 0.6 + i * 2.25;
      return [T(x, 4.65, 2.1, 0.32, P([blue(a)]), {size: 14}), T(x, 4.97, 2.1, 0.28, P([c]), {size: 9.5, color: C.grey})];
    }),
  ]});

/* 13. trackers */
add({kicker: 'Οι trackers του M5', title: 'HPT / HWT υλοποιημένοι και βαθμολογημένοι απέναντι σε ακριβείς μετρητές', notes:
  'Πέρα από το Figure 4, υλοποιήσαμε τους bounded trackers του M5: Space-Saving και Count-Min Sketch, τις δύο οικογένειες που συγκρίνει το paper στην ενότητα 5.1. '
  + 'Τρέχουν μέσα στο pintool δίπλα στους ακριβείς μετρητές, οπότε σε κάθε window ξέρουμε πόσο καλά βρίσκει ο tracker τις πραγματικά hot σελίδες — '
  + 'κάτι που το υλικό δεν μπορεί να ξέρει. Σε μικρά budgets το Space-Saving καλύπτει περίπου διπλάσια κίνηση από το Count-Min.',
  els: [
    I('docs/assets/deck/trackers.png', {x: 0.4, y: 1.3, w: 6.3, h: 3.85}, 'left'),
    body(6.85, 1.45, 2.65, 3.0, P(
      [b('Space-Saving'), ' και ', b('Count-Min Sketch'), ', οι δύο οικογένειες του M5 §5.1.'],
      ['Τρέχουν δίπλα στο PAC / WAC: ', b('ground truth σε κάθε window'), ', που το υλικό δεν έχει.'],
      ['Ένα πέρασμα: όλα τα budgets, 50 έως 8.192 entries.'],
    ), {size: 11, psa: 8}),
  ]});

/* 14. KV + granularity */
add({kicker: 'Πέρα από τα GAP', title: 'Στα key-value workloads η αραιότητα του M5 αναπαράγεται — και η μονάδα μέτρησης μετράει', notes:
  'Για τα key-value workloads το M5 δίνει αριθμούς στο κείμενο: 86% των σελίδων του Redis και 76% του Memcached έχουν το πολύ 25% των words τους προσπελασμένα. '
  + 'Εμείς μετράμε 80% και 78%. Τα τρέξαμε με δικό μας Zipfian client, σε μορφή YCSB-A, και με αλλαγές που έχουν σημασία: jemalloc όπως στο Redis και εγγραφές με 10 πεδία των 100 bytes. '
  + 'Δεξιά, τι γίνεται αν ο tracker μετρά σε μεγαλύτερη μονάδα από 64 bytes, για να κοστίζει λιγότερο. Στα 512 bytes το Redis φαίνεται 2,5 φορές πυκνότερο: '
  + 'ο φθηνότερος tracker κρύβει ακριβώς την αραιότητα που δικαιολογεί την ύπαρξη του HWT. Επίσης, το hot set του Redis είναι σταθερό — 97% παραμένει από window σε window.',
  els: [
    ...table(0.6, 1.45, [2.3, 0.85, 0.85], [
      ['σελίδες με ≤ 25% words', 'M5 (§4)', 'εδώ'],
      ['Redis (YCSB-A)', '86%', '80%'],
      ['Memcached', '76%', '78%'],
    ], {size: 12, rowH: 0.45, align: ['left', 'right', 'right']}),
    body(0.6, 2.95, 4.0, 2.25, P(
      ['Zipfian client σε μορφή YCSB-A · ', b('jemalloc'), ' · εγγραφές 10 × 100 B.'],
      ['Hot set του Redis σταθερό: ', b('97%'), ' του top-128 μένει από window σε window· στα GAP έως 19%.'],
    ), {size: 11, psa: 8}),
    I('docs/assets/deck/granularity.png', {x: 4.7, y: 1.3, w: 4.85, h: 3.35}),
    T(4.85, 4.7, 4.6, 0.55, P(['Σε μονάδα 512 B το Redis φαίνεται ', b('2,5× πυκνότερο'), ': ο φθηνός tracker κρύβει την αραιότητα.']),
      {size: 11, color: C.ink}),
  ]});

/* 15. infrastructure */
add({kicker: 'Υποδομή και αναπαραγωγιμότητα', title: 'Κάθε αριθμός μπορεί να ελεγχθεί και να ξανατρέξει', notes:
  'Λίγα λόγια για την υποδομή, γιατί κάνει τα αποτελέσματα αξιόπιστα. Η τελική καμπάνια είναι 1,74 τρισεκατομμύρια instructions και 461 δισεκατομμύρια αναφορές μνήμης κάτω από Pin, '
  + 'και ο προσομοιωτής 62 ώρες full-system εκτέλεσης. Κάθε run γράφει manifest με την εντολή και τα hashes. Τα μεγάλα runs είναι ανθεκτικά σε διακοπές: '
  + 'το pintool γράφει snapshot κάθε 32 epochs, ο προσομοιωτής κάνει checkpoint με DMTCP. Κάναμε και συστηματικό εσωτερικό έλεγχο του κώδικα, '
  + 'με διορθώσεις όπως η σωστή χρήση του predication του Pin· όλοι οι αριθμοί που είδατε είναι από το διορθωμένο εργαλείο. '
  + 'Τέλος, μετρήσαμε γιατί το Pin κλιμακώνεται άσχημα σε 20 threads: το 89–90% του χρόνου είναι σε εσωτερικό lock του Pin — αυτό είναι το επόμενο engineering βήμα.',
  els: [
    ...[['1,74 τρισ.', 'instructions υπό Pin'], ['461 δισ.', 'αναφορές μνήμης'], ['62 ώρες', 'full-system προσομοίωση'], ['95', 'commits, με τεκμηρίωση']]
      .flatMap(([a, c], i) => {
        const x = 0.6 + i * 2.25;
        return [T(x, 1.4, 2.1, 0.5, P([blue(a)]), {size: 22}), T(x, 1.9, 2.1, 0.3, P([c]), {size: 10, color: C.grey})];
      }),
    L(0.6, 2.4, 9.4, 2.4, {color: C.rule}),
    body(0.6, 2.6, 4.25, 2.6, P(
      [b('Manifest ανά run: '), 'εντολή, SHA-256 εργαλείου, binary και input, χρόνος, κατάσταση.'],
      [b('Ανθεκτικότητα: '), 'snapshot του pintool κάθε 32 epochs· checkpoint / restore του προσομοιωτή με DMTCP.'],
    ), {size: 11.5, psa: 9}),
    body(5.15, 2.6, 4.25, 2.6, P(
      [b('Εσωτερικός έλεγχος κώδικα: '), 'Pin predication, dirty writebacks, placement — όλοι οι αριθμοί είναι από το διορθωμένο εργαλείο.'],
      [b('Scalability: '), 'σε 20 threads, 89–90% του CPU σε εσωτερικό lock του Pin — εντοπισμένο επόμενο βήμα.'],
    ), {size: 11.5, psa: 9}),
  ]});

/* ---------- detailed results (16-18) ---------- */
add({kicker: 'Λεπτομέρειες', title: 'Πίνακας αποτελεσμάτων ανά workload', notes:
  'Αναλυτικά τα νούμερα. Η στήλη «αρχικό» είναι το demand-only μοντέλο με window 10M events. Η στήλη «τελικό» είναι το μοντέλο με prefetching, με κοινό time window που επιλέγεται leave-one-out. '
  + 'Η στήλη «ολόκληρη εκτέλεση» είναι το σφάλμα αν μετρήσουμε όλη την εκτέλεση σαν ένα μόνο window, χωρίς να διαλέξουμε μήκος: είναι το απλούστερο σημείο αναφοράς, και δείχνει ότι το κοινό window βοηθά κυρίως στα BFS και TC. Τα BC και SSSP έτρεξαν με 4 και 8 trials αντί για 100 και 200 του artifact, για λόγους χρόνου κάτω από Pin.',
  els: [
    ...table(0.6, 1.35, [1.0, 2.45, 0.85, 1.35, 1.35, 1.75], [
      ['Workload', 'Dataset', 'Trials', 'Αρχικό', 'Τελικό', 'Ολόκληρη εκτ.'],
      ...WL.map(w => {
        const fam = {bfs: 'Twitter (hash75)', cc: 'Twitter (hash75)', pr: 'Twitter (hash75)', tc: 'Twitter (hash25)', bc: 'Google+ snapshot 4', sssp: 'Google+ snapshot 2'}[w];
        const tri = {bfs: '200', cc: '3', pr: '1', tc: '1', bc: '4', sssp: '8'}[w];
        return [NAME[w], fam, tri, f2(CARD[w].old_epoch), f2(CARD[w].loo_error), f2(CARD[w].new_whole)];
      }),
      ['Μέσος', '', '', MEAN_OLD, MEAN_NEW, f2(mean('new_whole'))],
    ], {size: 11.5, rowH: 0.41, align: ['left', 'left', 'right', 'right', 'right', 'right'], hl: 7}),
    T(0.6, 4.75, 8.75, 0.5, P(
      [b('Αρχικό: '), 'χωρίς prefetchers, window 10M events.  ', b('Τελικό: '), 'με prefetchers, κοινό window σε χρόνο.'],
      [b('Ολόκληρη εκτ.: '), 'όλη η εκτέλεση μετρημένη ως ένα window, δηλαδή χωρίς καμία επιλογή μήκους.'],
    ), {size: 10, color: C.grey, psa: 2}),
  ]});

add({kicker: 'Λεπτομέρειες', title: 'Έλεγχοι ευαισθησίας: threads, LLC ways, setup και trials', notes:
  'Πριν βρούμε τους μηχανισμούς, ελέγξαμε τις προφανείς διαφορές από το setup του M5, μία-μία, με το αρχικό μοντέλο: 20 threads, μέτρηση μαζί με το setup της εφαρμογής, '
  + '200 trials, 9 αντί για 10 ways. Όλα μένουν γύρω στο 0.5 — κανένα δεν πλησιάζει το M5. Αυτό μας έδειξε ότι κάτι έλειπε από το ίδιο το μοντέλο: το prefetching και ο ορισμός του window.',
  els: [
    ...table(0.6, 1.4, [4.6, 2.0, 2.0], [
      ['Έλεγχος (demand-only μοντέλο, 10M window)', 'BFS', 'CC'],
      ['βάση: 1 thread, 1 trial', '0.556', '0.492'],
      ['20 threads, όπως το M5', '0.560', '0.493'],
      ['με το setup της εφαρμογής (full process)', '0.507', '0.448'],
      ['200 trials', '0.596', '0.580'],
      ['9 αντί για 10 LLC ways', '0.549', '0.492'],
    ], {size: 12, rowH: 0.45, align: ['left', 'right', 'right']}),
    T(0.6, 4.3, 8.8, 0.8, P(['Κανένας έλεγχος δεν φέρνει το σφάλμα κοντά στο M5: όλα μένουν γύρω στο 0.45–0.6. Άρα η διαφορά βρισκόταν σε μηχανισμό που έλειπε — ',
      b('hardware prefetching'), ' — και στον ορισμό του ', b('window'), '.']), {size: 12, color: C.ink}),
  ]});

add({kicker: 'Λεπτομέρειες', title: 'Οι καμπύλες: M5, αρχικό μοντέλο, τελικό μοντέλο', notes:
  'Τα ίδια δεδομένα ως καμπύλες. Μαύρο το M5, κόκκινο το αρχικό μοντέλο, μπλε το τελικό.',
  els: [I('docs/assets/fig4_prefetch_ladder.png', {x: 0.4, y: 1.3, w: 9.2, h: 3.95})]});

/* 19. future work (closing slide) */
add({kicker: 'Επόμενα βήματα', title: 'Μελλοντικά βήματα', notes:
  'Κλείνω με τα επόμενα βήματα. Πρώτο, το Liblinear και οι υπόλοιπες ρυθμίσεις στον προσομοιωτή, για να έχουμε τη σύγκριση με ορατό τον kernel. '
  + 'Δεύτερο, multithreaded Pin χωρίς το κοινό lock, ώστε να τρέξουμε με 20 threads όπως το M5. Τρίτο, για το CC: οι L1 prefetchers και τα LLC-only prefetches, '
  + 'που δεν είναι ακόμα στο μοντέλο, είναι οι φυσικοί υποψήφιοι για το N=48. Τέταρτο, έχουμε έτοιμο ερώτημα προς τους συγγραφείς για το collection interval του Figure 4. '
  + 'Και όταν δημοσιευτεί το CXLRAMSim, ο μετρητής μεταφέρεται όπως μεταφέρθηκε στο SimCXL. Ευχαριστώ πολύ — ερωτήσεις;',
  els: [
    ...[['Liblinear και υπόλοιπα στον προσομοιωτή', 'η ίδια σύγκριση με ορατό τον kernel, με checkpoint / restore'],
      ['Multithreaded Pin χωρίς το κοινό lock', '20 threads, όπως το testbed του M5'],
      ['CC: L1 και LLC-only prefetchers στο μοντέλο', 'οι φυσικοί υποψήφιοι για το N = 48'],
      ['Ερώτημα προς τους συγγραφείς', 'το collection interval του Figure 4 — έτοιμο προσχέδιο'],
      ['CXLRAMSim, όταν δημοσιευτεί', 'ο μετρητής μεταφέρεται όπως στο SimCXL']].flatMap(([a, c], i) => {
      const y = 1.4 + i * 0.6;
      return [T(0.6, y, 0.4, 0.5, P([String(i + 1)]), {size: 16, bold: true, color: C.blue}),
        T(1.05, y + 0.02, 4.6, 0.28, P([a]), {size: 12.5, bold: true, color: C.ink}),
        T(1.05, y + 0.29, 4.6, 0.26, P([c]), {size: 10.5, color: C.grey})];
    }),
    R(6.3, 1.4, 3.1, 2.5, {fill: C.paper}),
    T(6.5, 1.55, 2.8, 0.35, P(['Συνοπτικά']), {size: 12.5, bold: true, color: C.blue}),
    body(6.5, 1.95, 2.8, 2.4, P(
      [b(`Figure 4: ${MEAN_NEW}`), ' μέσο max σφάλμα σε 6 GAP workloads'],
      [b('Μοντέλο cache: '), 'σφάλμα 0.25 → 0.11'],
      [b('SimCXL: '), 'PR 0.02, BFS 0.12, CC 0.17'],
      [b('Trackers, granularity, KV')],
    ), {size: 11, psa: 7}),
    T(6.3, 4.25, 3.1, 0.6, P([b('Ευχαριστώ — ερωτήσεις;')], [{t: 'github.com/Zajason/memory_tiering', c: C.grey}]),
      {size: 12, color: C.ink, psa: 2}),
  ]});

/* ---------- slide chrome + element normalisation, shared by both back ends ---------- */
function chrome(sd, i, total) {
  const band = R(0, 0, 0.32, H, {fill: C.ink});
  if (!sd.title) return [band];
  const cur = SECTIONS.findIndex(([, ks]) => ks.includes(sd.kicker));
  const label = sd.backup ? 'Backup' : `${String(cur + 1).padStart(2, '0')}  ${SECTIONS[cur][0]}`;
  return [
    band,
    // rotated 270°: box centred on the band, text reads bottom-to-top, right-aligned = starts at the top
    T(0.16 - 2.0, 2.2 - 0.16, 4.0, 0.32, P([label]), {size: 8.5, color: 'C9CCCF', align: 'right', valign: 'middle', rot: 270}),
    T(0, 5.12, 0.32, 0.3, P([sd.backup ? 'B' : `${i + 1}`]), {size: 10, color: C.white, align: 'center', font: SERIF}),
    T(0.6, 0.36, 8.8, 0.7, P([sd.title]), {size: 18, bold: true, color: C.ink, lh: 0.98, font: SERIF}),
  ];
}
// tinted call-out panels become margin notes: no fill, one vertical rule on the left
function normalise(e) {
  if (e.k === 'rect' && !e.o.line && (e.o.fill === C.blueBg || e.o.fill === C.paper))
    return [L(e.x, e.y + 0.04, e.x, e.y + e.h - 0.04, {color: e.o.fill === C.blueBg ? C.blue : C.light, w: 2})];
  return [e];
}
const allEls = (sd, i, total) => [...chrome(sd, i, total), ...sd.els.flatMap(normalise)];

/* ---------- back end: PowerPoint ---------- */
function runsPptx(paras, o) {
  const out = [];
  paras.forEach((p, pi) => {
    p.forEach((r, ri) => {
      const run = typeof r === 'string' ? {t: r} : r;
      const opt = {};
      if (run.b) opt.bold = true;
      if (run.c) opt.color = run.c;
      if (run.i) opt.italic = true;
      if (run.f) opt.fontFace = run.f;
      if (ri === p.length - 1 && pi < paras.length - 1) opt.breakLine = true;
      out.push({text: run.t, options: opt});
    });
  });
  return out;
}

function drawPptx(pptx) {
  const total = slides.filter(s => !s.backup).length;
  slides.forEach((sd, i) => {
    const s = pptx.addSlide();
    s.background = {color: C.white};
    for (const e of allEls(sd, i, total)) {
      if (e.k === 'rect') s.addShape(pptx.ShapeType.rect, {x: e.x, y: e.y, w: e.w, h: e.h,
        fill: {color: e.o.fill || C.white}, line: e.o.line ? {color: e.o.line, width: e.o.lw || 0.75} : {type: 'none'}});
      else if (e.k === 'line') s.addShape(pptx.ShapeType.line, {x: Math.min(e.x1, e.x2), y: Math.min(e.y1, e.y2),
        w: Math.abs(e.x2 - e.x1), h: Math.abs(e.y2 - e.y1), flipV: false,
        line: {color: e.o.color || C.rule, width: e.o.w || 0.75, ...(e.o.arrow ? {endArrowType: 'triangle'} : {})}});
      else if (e.k === 'image') s.addImage({path: e.p, x: e.x, y: e.y, w: e.w, h: e.h});
      else if (e.k === 'text') {
        const o = e.o;
        s.addText(runsPptx(e.content, o), {x: e.x, y: e.y, w: e.w, h: e.h, fontFace: o.font || FONT, fontSize: o.size || 12,
          color: o.color || C.ink, bold: !!o.bold, italic: !!o.i, align: o.align || 'left', valign: o.valign || 'top', margin: 0,
          paraSpaceAfter: o.psa || 0, lineSpacingMultiple: o.lh || 1.12, ...(o.rot ? {rotate: o.rot} : {})});
      }
    }
    if (sd.notes) s.addNotes(sd.notes);
  });
}

/* ---------- back end: HTML preview ---------- */
const esc = t => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const PX = 96, PT = 96 / 72;
function htmlText(e) {
  const o = e.o;
  const paras = e.content.map((p, pi) => `<p style="margin:0 0 ${pi < e.content.length - 1 ? (o.psa || 0) * PT : 0}px">` + p.map(r => {
    const run = typeof r === 'string' ? {t: r} : r;
    const st = [run.b ? 'font-weight:700' : '', run.c ? `color:#${run.c}` : '', run.i ? 'font-style:italic' : '',
      run.f ? `font-family:'${run.f}',monospace;white-space:pre` : ''].filter(Boolean).join(';');
    return st ? `<span style="${st}">${esc(run.t)}</span>` : esc(run.t);
  }).join('') + '</p>').join('');
  const jc = {top: 'flex-start', middle: 'center', bottom: 'flex-end'}[o.valign || 'top'];
  return `<div class="t" style="left:${e.x * PX}px;top:${e.y * PX}px;width:${e.w * PX}px;height:${e.h * PX}px;`
    + `${o.rot ? `transform:rotate(-${360 - o.rot}deg);` : ''}${o.font ? `font-family:'${o.font}',serif;` : ''}font-size:${(o.size || 12) * PT}px;color:#${o.color || C.ink};font-weight:${o.bold ? 700 : 400};${o.i ? 'font-style:italic;' : ''}`
    + `text-align:${o.align || 'left'};justify-content:${jc};line-height:${(o.lh || 1.12) * 1.2}">${paras}</div>`;
}
function drawHtml() {
  const total = slides.filter(s => !s.backup).length;
  const pages = slides.map((sd, i) => {
    const parts = [];
    let svg = '';
    for (const e of allEls(sd, i, total)) {
      if (e.k === 'rect') parts.push(`<div style="position:absolute;left:${e.x * PX}px;top:${e.y * PX}px;width:${e.w * PX}px;height:${e.h * PX}px;`
        + `background:#${e.o.fill || C.white};box-sizing:border-box;${e.o.line ? `border:${(e.o.lw || 0.75) * PT}px solid #${e.o.line}` : ''}"></div>`);
      else if (e.k === 'image') parts.push(`<img src="file://${e.p}" style="position:absolute;left:${e.x * PX}px;top:${e.y * PX}px;width:${e.w * PX}px;height:${e.h * PX}px">`);
      else if (e.k === 'line') svg += `<line x1="${e.x1 * PX}" y1="${e.y1 * PX}" x2="${e.x2 * PX}" y2="${e.y2 * PX}" stroke="#${e.o.color || C.rule}" stroke-width="${(e.o.w || 0.75) * PT}" ${e.o.arrow ? 'marker-end="url(#a)"' : ''}/>`;
      else if (e.k === 'text') parts.push(htmlText(e));
    }
    return `<section>${parts.join('')}<svg width="${W * PX}" height="${H * PX}"><defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#${C.grey}"/></marker></defs>${svg}</svg></section>`;
  });
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>preview</title><style>
@page{size:${W}in ${H}in;margin:0}body{margin:0;background:#ccc;font-family:'${FONT}',sans-serif}
section{position:relative;width:${W * PX}px;height:${H * PX}px;background:#fff;overflow:hidden;margin:0 auto 12px;page-break-after:always}
@media print{body{background:#fff}section{margin:0}}
.t{position:absolute;display:flex;flex-direction:column;overflow:visible;box-sizing:border-box}
.k{letter-spacing:1.5px}svg{position:absolute;left:0;top:0;pointer-events:none}</style></head><body>${pages.join('\n')}</body></html>`;
}

const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_16x9';
pptx.author = 'Ιάσων Ζακυνθινός';
pptx.title = 'Sub-page hot skewness σε CXL tiered memory';
drawPptx(pptx);
await pptx.writeFile({fileName: OUT});
mkdirSync(path.dirname(PREVIEW), {recursive: true});
writeFileSync(PREVIEW, drawHtml());
console.log('wrote', OUT, `(${slides.length} slides)`);
console.log('wrote', PREVIEW);
