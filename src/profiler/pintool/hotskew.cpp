/*
 * hotskew.cpp -- cache-line-granularity hot-skewness profiler.
 *
 * Reproduces, in software, the measurement that M5 (ASPLOS'25) took with FPGA
 * hardware: how the accesses to a 4 KB page are distributed across its sixty-four
 * 64 B words. Specifically it produces the data behind
 *
 *   Figure 4  -- P(a 4 KB page has at most N unique 64 B words accessed),
 *                for N in {4, 8, 16, 32, 48}
 *   Figure 10 -- distribution of access counts per 4 KB page
 *
 * Pipeline:
 *
 *   Pin memory refs --> [L1d] --> [L2] --> [LLC] --> DRAM stream --> PAC/WAC counters
 *                        per-thread        shared     (misses +      (counter_table.hpp)
 *                                                      dirty WBs)
 *
 * The cache filter is not decoration. M5's counters live in the CXL controller and
 * only ever see post-LLC traffic; counting raw loads and stores instead would answer
 * a different question. `-cache 0` disables the filter so the two can be compared --
 * that comparison is itself a result worth showing.
 *
 * Build:  make PIN_ROOT=/path/to/pin
 * Run:    $PIN_ROOT/pin -t obj-intel64/hotskew.so -o out/run -- ./bench args
 */

#include "pin.H"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "cache_model.hpp"
#include "counter_table.hpp"
#include "tracker.hpp"

using namespace hotskew;
using std::string;

/* ------------------------------------------------------------------ knobs */

KNOB<string> KnobOut(KNOB_MODE_WRITEONCE, "pintool", "o", "hotskew",
                     "output prefix (writes <prefix>.summary.txt, <prefix>.epochs.csv, "
                     "<prefix>.pages.bin)");
KNOB<string> KnobTag(KNOB_MODE_WRITEONCE, "pintool", "tag", "",
                     "benchmark label recorded in the output (defaults to the image name)");

// --- cache geometry. Defaults mirror Intel Xeon 6430 (Sapphire Rapids), the CPU in
// --- M5's own testbed, so our filter has the same strength as theirs.
KNOB<UINT32> KnobCacheOn(KNOB_MODE_WRITEONCE, "pintool", "cache", "1",
                         "1 = filter through the cache hierarchy (PAC/WAC semantics), "
                         "0 = count every architectural load/store");
KNOB<UINT64> KnobL1Size(KNOB_MODE_WRITEONCE, "pintool", "l1_kb", "48", "L1d size in KB (per thread)");
KNOB<UINT32> KnobL1Assoc(KNOB_MODE_WRITEONCE, "pintool", "l1_assoc", "12", "L1d associativity");
KNOB<UINT64> KnobL2Size(KNOB_MODE_WRITEONCE, "pintool", "l2_kb", "2048", "L2 size in KB (per thread)");
KNOB<UINT32> KnobL2Assoc(KNOB_MODE_WRITEONCE, "pintool", "l2_assoc", "16", "L2 associativity");
KNOB<UINT64> KnobL3Size(KNOB_MODE_WRITEONCE, "pintool", "l3_kb", "61440", "LLC size in KB (shared)");
KNOB<UINT32> KnobL3Assoc(KNOB_MODE_WRITEONCE, "pintool", "l3_assoc", "15", "LLC associativity");
KNOB<UINT32> KnobCountWB(KNOB_MODE_WRITEONCE, "pintool", "count_wb", "1",
                         "count dirty LLC writebacks as DRAM accesses (PAC snoops them too)");

// --- measurement window. See docs/methodology.md, "Why epochs are mandatory".
// All three are in millions of *instructions*, counted at basic-block granularity.
// Using one clock for every phase transition keeps the semantics obvious; memory
// references are counted per thread and never drive control flow, so they cost
// nothing in contention.
KNOB<UINT64> KnobFastForward(KNOB_MODE_WRITEONCE, "pintool", "ff", "0",
                             "skip this many instructions before profiling (Millions)");
KNOB<UINT64> KnobWarmup(KNOB_MODE_WRITEONCE, "pintool", "warmup", "0",
                        "instructions spent warming the caches without counting (Millions)");
KNOB<UINT64> KnobLength(KNOB_MODE_WRITEONCE, "pintool", "len", "0",
                        "stop after this many profiled instructions (Millions); 0 = to completion");
KNOB<UINT64> KnobEpoch(KNOB_MODE_WRITEONCE, "pintool", "epoch", "50",
                       "DRAM accesses per measurement epoch (Millions); 0 = one epoch for the "
                       "whole run");
// A window measured in DRAM accesses normalises away the effect of cache size: a
// smaller cache emits more DRAM accesses, so a fixed number of them spans less
// execution. To ask "what does the controller see in a fixed slice of *time*" --
// which is what M5's 10 ms PAC dumps ask -- the window has to be defined in
// instructions instead. Set this and it takes precedence over -epoch.
KNOB<UINT64> KnobEpochIns(KNOB_MODE_WRITEONCE, "pintool", "epoch_ins", "0",
                          "instructions per measurement epoch (Millions); a time-proportional "
                          "window, overrides -epoch when non-zero");
KNOB<UINT32> KnobMaxEpochs(KNOB_MODE_WRITEONCE, "pintool", "max_epochs", "0",
                           "detach after this many epochs; 0 = unlimited");

// --- region-of-interest by routine name, for benchmarks that spend most of their
// --- time in setup (GAPBS graph construction, Redis dataset load, ...).
KNOB<string> KnobRoiRtn(KNOB_MODE_WRITEONCE, "pintool", "roi_rtn", "",
                        "profile only inside this routine (matched as a substring of the "
                        "symbol name); enables on entry, disables on return");
KNOB<string> KnobRoiBegin(KNOB_MODE_WRITEONCE, "pintool", "roi_begin", "",
                          "routine whose entry starts profiling (pairs with -roi_end); use with "
                          "the markers in src/profiler/roi/hotskew_roi.h");
KNOB<string> KnobRoiEnd(KNOB_MODE_WRITEONCE, "pintool", "roi_end", "",
                        "routine whose entry stops profiling");
KNOB<UINT32> KnobRoiEpoch(KNOB_MODE_WRITEONCE, "pintool", "roi_epoch", "1",
                          "close the current epoch each time the ROI is left, so that one "
                          "epoch never spans two invocations");

// --- bounded top-K trackers: M5's HPT and HWT (tracker.hpp).
//
// These are the hardware M5 proposes. Running them next to the exact counters means
// every profiling run also scores the approximation against ground truth, which is
// M5's Figure 8 metric and normally needs their FPGA to obtain.
KNOB<UINT32> KnobTrack(KNOB_MODE_WRITEONCE, "pintool", "track", "0",
                       "1 = also run bounded top-K trackers (HPT/HWT) and score them "
                       "against the exact counts at every epoch boundary");
KNOB<string> KnobTrackAlgo(KNOB_MODE_WRITEONCE, "pintool", "track_algo", "spacesaving",
                           "spacesaving | cmsketch -- the two families M5 compares");
KNOB<string> KnobTrackN(KNOB_MODE_WRITEONCE, "pintool", "track_n", "512",
                        "tracker budget N: entries (Space-Saving) or D*W counters "
                        "(CM-Sketch). Comma-separated for a sweep, e.g. 50,128,512,2048 "
                        "-- every budget is fed the same stream in one pass, so the whole "
                        "accuracy-vs-cost curve costs one run instead of one run per point");
KNOB<UINT32> KnobTrackK(KNOB_MODE_WRITEONCE, "pintool", "track_k", "128",
                        "K: how many hot pages the tracker is asked to report");
KNOB<UINT32> KnobTrackDepth(KNOB_MODE_WRITEONCE, "pintool", "track_depth", "2",
                            "CM-Sketch rows D (NeoMem uses D=2); width W = track_n / D");
KNOB<UINT32> KnobTrackWord(KNOB_MODE_WRITEONCE, "pintool", "track_word", "1",
                           "also run the Hot Word Tracker (64 B granularity), gated on "
                           "pages the HPT currently holds -- this is M5's HWT");

// --- raw dump control.
KNOB<UINT32> KnobDumpPages(KNOB_MODE_WRITEONCE, "pintool", "dump_pages", "1",
                           "write the per-page raw records to <prefix>.pages.bin");
KNOB<UINT64> KnobDumpMinAccesses(KNOB_MODE_WRITEONCE, "pintool", "dump_min", "1",
                                 "only dump pages with at least this many accesses in the epoch");

/* ------------------------------------------------------- global tool state */

namespace {

enum Phase { PHASE_FASTFORWARD, PHASE_WARMUP, PHASE_PROFILE, PHASE_DONE };

// `g_active` is read by an inlinable predicate on every memory reference, so keep it
// a plain scalar. It is 1 only while we want the heavyweight analysis to run.
ADDRINT g_active = 0;

Phase g_phase = PHASE_FASTFORWARD;
bool g_roiEnabled = true;  // false until we enter the ROI routine, if one was named

UINT64 g_ffTarget = 0, g_warmupTarget = 0, g_lenTarget = 0, g_epochTarget = 0;
UINT64 g_insCount = 0;         // instructions retired (BBL-granular)
UINT64 g_profileStartIns = 0;  // g_insCount when the profile phase began
UINT64 g_epochStartIns = 0;    // g_insCount when the current epoch began
UINT64 g_epochInsTarget = 0;   // instructions per epoch (0 = use g_epochTarget)
UINT64 g_memRefs = 0;          // memory refs, summed from all threads in onFini
UINT64 g_dramAccesses = 0;     // accesses that reached the DRAM stream, this epoch
UINT32 g_epochId = 0;

bool g_useCache = true;
bool g_countWB = true;

CounterTable g_counters;

// HPT/HWT. Guarded by g_lock along with the counter table, since both are updated
// from the same point in the DRAM path.
bool g_track = false;
bool g_trackWord = false;
bool g_trackCM = false;

// One of these per hardware budget under test. They all see the same access stream
// in the same run, so the accuracy-vs-cost curve comes from a single execution.
struct TrackerSlot {
    UINT32 n = 0;
    SpaceSaving hpt, hwt;
    CountMinTopK hptCM, hwtCM;
    double hptRatioSum = 0.0, hptRecallSum = 0.0;
    double hwtRatioSum = 0.0, hwtRecallSum = 0.0;
};
std::vector<TrackerSlot*> g_slots;
std::ofstream g_trackCsv;
UINT32 g_trackEpochs = 0;

CacheLevel g_llc;
PIN_LOCK g_lock;

// Per-thread private levels.
struct ThreadState {
    CacheLevel l1;
    CacheLevel l2;
    UINT64 refs;
    UINT8 pad[64];  // keep neighbouring threads off the same line
};
TLS_KEY g_tlsKey;
std::vector<ThreadState*> g_threads;
PIN_LOCK g_threadsLock;

string g_outPrefix, g_tag;
std::ofstream g_epochCsv;
FILE* g_pagesBin = NULL;

// Aggregated across epochs: for each N, how many (page, epoch) observations had at
// most N unique words touched. Index by unique-word-count 0..64.
UINT64 g_uniqueWordHist[kWordsPerPage + 1];
// Figure 10: log2 histogram of per-page access counts.
UINT64 g_pageAccessHist[64];
UINT64 g_pagesObserved = 0;
UINT64 g_wordsTouchedTotal = 0;
UINT64 g_accessesInTopWordsTotal = 0;  // accesses landing in a page's hottest 4 words
UINT64 g_accessesTotal = 0;

/* ----------------------------------------------------------- helpers */

ThreadState* threadState(THREADID tid) {
    return static_cast<ThreadState*>(PIN_GetThreadData(g_tlsKey, tid));
}

// One DRAM access reached the "device". Caller holds g_lock.
inline void recordDram(UINT64 lineAddr, bool isWrite) {
    g_counters.record(lineAddr, isWrite);
    ++g_dramAccesses;

    if (g_track) {
        // HPT is keyed on the 4 KB page. lineAddr is already a 64 B line number, so
        // the page number is lineAddr >> 6.
        const UINT64 page = lineAddr >> (kPageShift - kWordShift);
        for (size_t i = 0; i < g_slots.size(); ++i) {
            TrackerSlot& t = *g_slots[i];
            if (g_trackCM) {
                t.hptCM.access(page);
                if (g_trackWord) t.hwtCM.access(lineAddr);
            } else {
                t.hpt.access(page);
                // HWT sees a word address only if the HPT currently holds its page.
                // That gating is what keeps the word tracker small: it never sees
                // addresses from pages nobody thinks are hot.
                if (g_trackWord && t.hpt.contains(page)) t.hwt.access(lineAddr);
            }
        }
    }
}

void finishEpoch();

/* -------------------------------------------------------- analysis path */

// Inlinable gate. Pin will fold this into the generated code.
ADDRINT PIN_FAST_ANALYSIS_CALL isActive() { return g_active; }

// The real work: push one access through the hierarchy and, if it falls out the
// bottom, into the PAC/WAC counters. `size` may straddle cache lines.
VOID analyzeMemRef(THREADID tid, ADDRINT addr, UINT32 size, BOOL isWrite) {
    ThreadState* ts = threadState(tid);
    if (ts == NULL) return;

    const UINT64 firstLine = (UINT64)addr >> kWordShift;
    const UINT64 lastLine = ((UINT64)addr + size - 1) >> kWordShift;
    const AccessType type = isWrite ? ACCESS_WRITE : ACCESS_READ;

    for (UINT64 line = firstLine; line <= lastLine; ++line) {
        // Per-thread and uncontended. Summed in onFini.
        ++ts->refs;

        if (!g_useCache) {
            PIN_GetLock(&g_lock, tid + 1);
            if (g_phase == PHASE_PROFILE) recordDram(line, isWrite);
            if (g_epochTarget && g_dramAccesses >= g_epochTarget) finishEpoch();
            PIN_ReleaseLock(&g_lock);
            continue;
        }

        // L1 and L2 are private to the thread: no lock, no shared writes. The vast
        // majority of references stop here, which is what keeps multithreaded runs
        // from serialising on the LLC lock.
        Outcome o1 = ts->l1.access(line, type);
        if (o1.hit) continue;

        // An L1 dirty eviction is a write into L2; the demand miss also fills L2.
        if (o1.wroteBack) ts->l2.access(o1.wbLineAddr, ACCESS_WRITE);
        Outcome o2 = ts->l2.access(line, type);
        if (o2.hit) continue;

        // Only L2 misses reach shared state.
        PIN_GetLock(&g_lock, tid + 1);

        if (o2.wroteBack) {
            Outcome ow = g_llc.access(o2.wbLineAddr, ACCESS_WRITE);
            if (ow.wroteBack && g_countWB && g_phase == PHASE_PROFILE)
                recordDram(ow.wbLineAddr, true);
        }

        Outcome o3 = g_llc.access(line, type);
        if (!o3.hit && g_phase == PHASE_PROFILE) {
            // The fill: this is the read the CXL controller sees.
            recordDram(line, false);
        }
        if (o3.wroteBack && g_countWB && g_phase == PHASE_PROFILE)
            recordDram(o3.wbLineAddr, true);

        if (g_epochTarget && g_dramAccesses >= g_epochTarget) finishEpoch();

        PIN_ReleaseLock(&g_lock);
    }
}

// Phase advance, driven by the instruction counter at basic-block granularity.
VOID PIN_FAST_ANALYSIS_CALL countBbl(UINT32 numIns) {
    g_insCount += numIns;

    switch (g_phase) {
        case PHASE_FASTFORWARD:
            if (g_insCount >= g_ffTarget) {
                g_phase = g_warmupTarget ? PHASE_WARMUP : PHASE_PROFILE;
                g_active = g_roiEnabled ? 1 : 0;
            }
            break;
        case PHASE_WARMUP:
            if (g_insCount >= g_ffTarget + g_warmupTarget) {
                g_phase = PHASE_PROFILE;
                g_profileStartIns = g_insCount;
                g_epochStartIns = g_insCount;
            }
            break;
        case PHASE_PROFILE:
            if (g_lenTarget && g_insCount - g_profileStartIns >= g_lenTarget) {
                g_phase = PHASE_DONE;
                g_active = 0;
            } else if (g_epochInsTarget && g_roiEnabled &&
                       g_insCount - g_epochStartIns >= g_epochInsTarget) {
                // Time-proportional epoch boundary.
                //
                // Gated on g_roiEnabled: instructions keep retiring outside the
                // region of interest, and without the gate the timer would fire
                // there and emit epochs that recorded nothing. g_epochStartIns is
                // also reset on ROI entry, so the first epoch inside a region is a
                // full one rather than however much time had elapsed outside it.
                //
                // finishEpoch touches shared state, so take the lock. This fires
                // once per epoch, not per basic block, so the cost is irrelevant.
                PIN_GetLock(&g_lock, 1);
                g_epochStartIns = g_insCount;
                finishEpoch();
                PIN_ReleaseLock(&g_lock);
            }
            break;
        case PHASE_DONE:
            break;
    }
}

/* -------------------------------------------------- epoch bookkeeping */

// Fold the current epoch's counters into the aggregate histograms, optionally dump
// the raw records, then zero the table. Caller holds g_lock.
void finishEpoch() {
    // Nothing was recorded: do not burn an epoch id on it. An empty epoch would
    // otherwise inflate the reported epoch count and make the run look like it
    // sampled more windows than it actually did.
    if (g_counters.totalAccesses() == 0) return;

    UINT64 pagesThisEpoch = 0;
    UINT64 accessesThisEpoch = 0;
    UINT64 uniqueWordsThisEpoch = 0;
    UINT64 histThisEpoch[kWordsPerPage + 1];
    memset(histThisEpoch, 0, sizeof(histThisEpoch));

    const UINT64 dumpMin = KnobDumpMinAccesses.Value();

    g_counters.forEachTouchedPage([&](UINT64 pageNo, const PageRec& p) {
        const UINT64 total = p.reads + p.writes;
        const UINT32 unique = (UINT32)__builtin_popcountll(p.touchedMask);

        ++pagesThisEpoch;
        accessesThisEpoch += total;
        uniqueWordsThisEpoch += unique;
        ++histThisEpoch[unique];
        ++g_uniqueWordHist[unique];

        // Figure 10 axis: log2 bucket of the page's access count.
        UINT32 bucket = 0;
        UINT64 v = total;
        while (v > 1) { v >>= 1; ++bucket; }
        if (bucket > 63) bucket = 63;
        ++g_pageAccessHist[bucket];

        // Concentration: what share of the page's accesses land in its 4 hottest
        // words? This is the number that makes the "sparse hot page" case concrete.
        UINT16 top[4] = {0, 0, 0, 0};
        for (UINT32 w = 0; w < kWordsPerPage; ++w) {
            UINT16 c = p.word[w];
            if (c > top[0]) { top[3] = top[2]; top[2] = top[1]; top[1] = top[0]; top[0] = c; }
            else if (c > top[1]) { top[3] = top[2]; top[2] = top[1]; top[1] = c; }
            else if (c > top[2]) { top[3] = top[2]; top[2] = c; }
            else if (c > top[3]) { top[3] = c; }
        }
        g_accessesInTopWordsTotal += (UINT64)top[0] + top[1] + top[2] + top[3];

        if (g_pagesBin && total >= dumpMin) {
            // Record: epoch(u32) page(u64) reads(u64) writes(u64) mask(u64) word[64](u16)
            fwrite(&g_epochId, sizeof(UINT32), 1, g_pagesBin);
            fwrite(&pageNo, sizeof(UINT64), 1, g_pagesBin);
            fwrite(&p.reads, sizeof(UINT64), 1, g_pagesBin);
            fwrite(&p.writes, sizeof(UINT64), 1, g_pagesBin);
            fwrite(&p.touchedMask, sizeof(UINT64), 1, g_pagesBin);
            fwrite(p.word, sizeof(UINT16), kWordsPerPage, g_pagesBin);
        }
    });

    // ---- score HPT/HWT against the exact counts, before they are cleared ----
    //
    // This is M5's Figure 8: the access-count ratio of the addresses the bounded
    // tracker picked, over that of the true top-K. Doing it here, inside the same
    // epoch the tracker saw, is what makes the comparison exact rather than
    // approximate -- and it is the measurement their FPGA existed to obtain.
    if (g_track && pagesThisEpoch > 0) {
        std::unordered_map<UINT64, UINT64> exactPages, exactWords;
        exactPages.reserve(pagesThisEpoch * 2);
        g_counters.forEachTouchedPage([&](UINT64 pageNo, const PageRec& p) {
            exactPages[pageNo] = p.reads + p.writes;
            if (g_trackWord) {
                for (UINT32 w = 0; w < kWordsPerPage; ++w)
                    if (p.word[w])
                        exactWords[(pageNo << (kPageShift - kWordShift)) | w] = p.word[w];
            }
        });

        const UINT32 K = KnobTrackK.Value();
        for (size_t i = 0; i < g_slots.size(); ++i) {
            TrackerSlot& t = *g_slots[i];
            std::vector<UINT64> picked;
            if (g_trackCM) t.hptCM.topK(K, picked); else t.hpt.topK(K, picked);
            TrackerScore hpt = scoreTopK(picked, exactPages, K);

            TrackerScore hwt;
            if (g_trackWord) {
                std::vector<UINT64> pickedW;
                if (g_trackCM) t.hwtCM.topK(K, pickedW); else t.hwt.topK(K, pickedW);
                hwt = scoreTopK(pickedW, exactWords, K);
            }

            t.hptRatioSum += hpt.accessCountRatio;
            t.hptRecallSum += hpt.recall;
            t.hwtRatioSum += hwt.accessCountRatio;
            t.hwtRecallSum += hwt.recall;

            if (g_trackCsv.is_open()) {
                g_trackCsv << g_epochId << "," << K << "," << t.n << ","
                           << (g_trackCM ? "cmsketch" : "spacesaving") << ","
                           << std::fixed << std::setprecision(6)
                           << hpt.accessCountRatio << "," << hpt.recall << ","
                           << hwt.accessCountRatio << "," << hwt.recall << ","
                           << exactPages.size() << "," << exactWords.size() << "\n";
            }

            // Trackers reset with the counters: one epoch is one measurement window
            // for both, so they stay directly comparable.
            if (g_trackCM) { t.hptCM.reset(); t.hwtCM.reset(); }
            else { t.hpt.reset(); t.hwt.reset(); }
        }
        if (g_trackCsv.is_open()) g_trackCsv.flush();
        ++g_trackEpochs;
    }

    g_pagesObserved += pagesThisEpoch;
    g_accessesTotal += accessesThisEpoch;
    g_wordsTouchedTotal += uniqueWordsThisEpoch;

    // Per-epoch row: the CDF points the paper plots, plus context.
    if (g_epochCsv.is_open() && pagesThisEpoch > 0) {
        UINT64 cum = 0;
        double cdf[5];
        const UINT32 marks[5] = {4, 8, 16, 32, 48};
        UINT32 mi = 0;
        for (UINT32 n = 0; n <= kWordsPerPage && mi < 5; ++n) {
            cum += histThisEpoch[n];
            while (mi < 5 && marks[mi] == n) {
                cdf[mi] = (double)cum / (double)pagesThisEpoch;
                ++mi;
            }
        }
        g_epochCsv << g_epochId << "," << pagesThisEpoch << "," << accessesThisEpoch << ","
                   << std::fixed << std::setprecision(6)
                   << (double)uniqueWordsThisEpoch / (double)pagesThisEpoch << ","
                   << cdf[0] << "," << cdf[1] << "," << cdf[2] << "," << cdf[3] << "," << cdf[4]
                   << "\n";
        g_epochCsv.flush();
    }

    g_counters.resetCounters();
    g_dramAccesses = 0;
    ++g_epochId;

    if (KnobMaxEpochs.Value() && g_epochId >= KnobMaxEpochs.Value()) {
        g_phase = PHASE_DONE;
        g_active = 0;
    }
}

/* --------------------------------------------------------- instrumentation */

VOID instrumentTrace(TRACE trace, VOID*) {
    for (BBL bbl = TRACE_BblHead(trace); BBL_Valid(bbl); bbl = BBL_Next(bbl)) {
        BBL_InsertCall(bbl, IPOINT_ANYWHERE, (AFUNPTR)countBbl, IARG_FAST_ANALYSIS_CALL,
                       IARG_UINT32, BBL_NumIns(bbl), IARG_END);

        for (INS ins = BBL_InsHead(bbl); INS_Valid(ins); ins = INS_Next(ins)) {
            if (!INS_IsMemoryRead(ins) && !INS_IsMemoryWrite(ins)) continue;

            UINT32 numOps = INS_MemoryOperandCount(ins);
            for (UINT32 op = 0; op < numOps; ++op) {
                // Software prefetches are deliberately *not* skipped: prefetcht0 really
                // does pull a line in from memory, so the CXL controller would count it.
                const BOOL isWrite = INS_MemoryOperandIsWritten(ins, op);
                INS_InsertIfCall(ins, IPOINT_BEFORE, (AFUNPTR)isActive, IARG_FAST_ANALYSIS_CALL,
                                 IARG_END);
                INS_InsertThenCall(ins, IPOINT_BEFORE, (AFUNPTR)analyzeMemRef, IARG_THREAD_ID,
                                   IARG_MEMORYOP_EA, op, IARG_UINT32,
                                   INS_MemoryOperandSize(ins, op), IARG_BOOL, isWrite, IARG_END);
            }
        }
    }
}

VOID roiEnter() {
    g_roiEnabled = true;
    // Restart the time-proportional epoch clock, so the first epoch inside the
    // region is a full window rather than however long we spent outside it.
    g_epochStartIns = g_insCount;
    if (g_phase == PHASE_WARMUP || g_phase == PHASE_PROFILE) g_active = 1;
}

VOID roiExit() {
    g_roiEnabled = false;
    g_active = 0;
    // Close the epoch at the ROI boundary. Without this, a short kernel invocation
    // would leave a partial epoch open and the next invocation's accesses would be
    // merged into it -- which silently widens the measurement window and inflates
    // the apparent word coverage per page.
    if (KnobRoiEpoch.Value() && g_dramAccesses > 0) {
        PIN_GetLock(&g_lock, 1);
        finishEpoch();
        PIN_ReleaseLock(&g_lock);
    }
}

// Hook whichever of the three ROI knobs the user supplied. Symbol names are matched
// as substrings, so mangled C++ names work without the caller demangling anything.
VOID instrumentRoutine(RTN rtn, VOID*) {
    const string name = RTN_Name(rtn);
    const string& single = KnobRoiRtn.Value();
    const string& begin = KnobRoiBegin.Value();
    const string& end = KnobRoiEnd.Value();

    bool hooked = false;
    if (!single.empty() && name.find(single) != string::npos) {
        RTN_Open(rtn);
        RTN_InsertCall(rtn, IPOINT_BEFORE, (AFUNPTR)roiEnter, IARG_END);
        RTN_InsertCall(rtn, IPOINT_AFTER, (AFUNPTR)roiExit, IARG_END);
        RTN_Close(rtn);
        hooked = true;
    }
    if (!begin.empty() && name.find(begin) != string::npos) {
        RTN_Open(rtn);
        RTN_InsertCall(rtn, IPOINT_BEFORE, (AFUNPTR)roiEnter, IARG_END);
        RTN_Close(rtn);
        hooked = true;
    }
    if (!end.empty() && name.find(end) != string::npos) {
        RTN_Open(rtn);
        RTN_InsertCall(rtn, IPOINT_BEFORE, (AFUNPTR)roiExit, IARG_END);
        RTN_Close(rtn);
        hooked = true;
    }
    if (hooked) std::cerr << "[hotskew] ROI hooked: " << name << "\n";
}

VOID onThreadStart(THREADID tid, CONTEXT*, INT32, VOID*) {
    ThreadState* ts = new ThreadState();
    ts->refs = 0;
    if (g_useCache) {
        std::ostringstream n1, n2;
        n1 << "L1d[t" << tid << "]";
        n2 << "L2[t" << tid << "]";
        ts->l1.init(n1.str(), KnobL1Size.Value() * 1024, KnobL1Assoc.Value(), 1u << kWordShift);
        ts->l2.init(n2.str(), KnobL2Size.Value() * 1024, KnobL2Assoc.Value(), 1u << kWordShift);
    }
    PIN_SetThreadData(g_tlsKey, ts, tid);

    PIN_GetLock(&g_threadsLock, tid + 1);
    g_threads.push_back(ts);
    PIN_ReleaseLock(&g_threadsLock);
}

/* ------------------------------------------------------------------ output */

void writeSummary() {
    const string path = g_outPrefix + ".summary.txt";
    std::ofstream f(path.c_str());

    // Refuse to print a CDF over an empty population. A run that recorded nothing --
    // the application failed to start, the ROI markers were never reached, the whole
    // working set fit in the modelled LLC -- would otherwise produce a table of
    // plausible-looking zeros that reads like a real (and very sparse) result.
    if (g_pagesObserved == 0) {
        f << "# hotskew summary\n";
        f << "benchmark          " << g_tag << "\n";
        f << "STATUS             NO DATA\n\n";
        f << "Not a single 4 KB page recorded a DRAM access, so there is no\n"
             "distribution to report. Usual causes, in order of likelihood:\n"
             "  * the application exited early (check its stderr)\n"
             "  * -roi_begin / -roi_end never matched a symbol (the tool prints\n"
             "    'ROI hooked: <name>' for each match; no such line means no match)\n"
             "  * -ff / -len skipped past the whole execution\n"
             "  * the working set fit entirely in the modelled cache\n";
        f << "\ninstructions       " << g_insCount << "\n";
        f << "mem_refs_profiled  " << g_memRefs << "\n";
        f.close();
        std::cerr << "[hotskew] WARNING: no pages observed -- see " << path << "\n";
        return;
    }

    // Aggregate CDF over every (page, epoch) observation.
    UINT64 cum = 0;
    std::vector<double> cdf(kWordsPerPage + 1, 0.0);
    for (UINT32 n = 0; n <= kWordsPerPage; ++n) {
        cum += g_uniqueWordHist[n];
        cdf[n] = g_pagesObserved ? (double)cum / (double)g_pagesObserved : 0.0;
    }

    f << "# hotskew summary\n";
    f << "benchmark          " << g_tag << "\n";
    f << "cache_filter       " << (g_useCache ? "on" : "off") << "\n";
    if (g_useCache) {
        f << "l1d                " << KnobL1Size.Value() << " KB, " << KnobL1Assoc.Value()
          << "-way (per thread)\n";
        f << "l2                 " << KnobL2Size.Value() << " KB, " << KnobL2Assoc.Value()
          << "-way (per thread)\n";
        f << "llc                " << KnobL3Size.Value() << " KB, " << KnobL3Assoc.Value()
          << "-way (shared)\n";
        f << "count_writebacks   " << (g_countWB ? "yes" : "no") << "\n";
    }
    f << "epochs             " << g_epochId << "\n";
    if (g_epochInsTarget)
        f << "epoch_len_ins      " << g_epochInsTarget << "   (time-proportional window)\n";
    else
        f << "epoch_len_dram_acc " << g_epochTarget << "\n";
    f << "instructions       " << g_insCount << "\n";
    f << "mem_refs_profiled  " << g_memRefs << "\n";
    f << "dram_accesses      " << g_accessesTotal << "\n";
    if (g_useCache && g_memRefs) {
        f << "llc_miss_ratio     " << std::fixed << std::setprecision(6)
          << (double)g_accessesTotal / (double)g_memRefs << "  (DRAM accesses per memory ref)\n";
    }
    f << "page_observations  " << g_pagesObserved << "   (page x epoch pairs with >=1 access)\n";
    if (g_pagesObserved) {
        f << "mean_unique_words  " << std::fixed << std::setprecision(3)
          << (double)g_wordsTouchedTotal / (double)g_pagesObserved << " / 64\n";
    }
    if (g_accessesTotal) {
        f << "top4_word_share    " << std::fixed << std::setprecision(4)
          << (double)g_accessesInTopWordsTotal / (double)g_accessesTotal
          << "   (share of accesses in each page's 4 hottest words)\n";
    }

    if (g_track && g_trackEpochs) {
        f << "\n# M5 Figure 8: bounded top-K trackers vs the exact counts\n";
        f << "# tracker=" << (g_trackCM ? "CM-Sketch" : "Space-Saving")
          << "  K=" << KnobTrackK.Value() << "  epochs=" << g_trackEpochs << "\n";
        f << "# storage assumes a 36-bit tag (48-bit PA, 4 KB pages) + 32-bit counter\n";
        f << "# N, hpt_access_ratio, hpt_recall, hwt_access_ratio, hwt_recall, KB\n";
        for (size_t i = 0; i < g_slots.size(); ++i) {
            const TrackerSlot& t = *g_slots[i];
            const UINT64 kb = ((UINT64)t.n * (36 + 32)) / 8192;
            f << t.n << "," << std::fixed << std::setprecision(4)
              << (t.hptRatioSum / g_trackEpochs) << ","
              << (t.hptRecallSum / g_trackEpochs) << ","
              << (t.hwtRatioSum / g_trackEpochs) << ","
              << (t.hwtRecallSum / g_trackEpochs) << "," << kb << "\n";
        }
    }

    f << "\n# M5 Figure 4: P(page has at most N unique 64B words accessed)\n";
    const UINT32 marks[5] = {4, 8, 16, 32, 48};
    const char* pct[5] = {"6.25%", "12.5%", "25%", "50%", "75%"};
    f << "N       pct_of_page   P(<=N)\n";
    for (int i = 0; i < 5; ++i) {
        f << std::setw(3) << marks[i] << "     " << std::setw(9) << pct[i] << "   " << std::fixed
          << std::setprecision(4) << cdf[marks[i]] << "\n";
    }
    f << "\n# P(page has at least 48 of 64 words accessed) = " << std::fixed
      << std::setprecision(4) << (1.0 - cdf[47]) << "\n";

    f << "\n# full unique-word histogram (unique_words, page_observations)\n";
    for (UINT32 n = 0; n <= kWordsPerPage; ++n) f << n << "," << g_uniqueWordHist[n] << "\n";

    f << "\n# M5 Figure 10: log2 histogram of accesses per 4KB page per epoch\n";
    f << "# (log2_bucket, pages)  -- bucket b covers access counts [2^b, 2^(b+1))\n";
    for (UINT32 b = 0; b < 64; ++b) {
        if (g_pageAccessHist[b]) f << b << "," << g_pageAccessHist[b] << "\n";
    }
    f.close();

    std::cerr << "[hotskew] wrote " << path << "\n";
}

VOID onFini(INT32, VOID*) {
    PIN_GetLock(&g_lock, 1);
    // Roll the per-thread reference counters up now that every thread has stopped.
    PIN_GetLock(&g_threadsLock, 1);
    g_memRefs = 0;
    for (size_t i = 0; i < g_threads.size(); ++i) g_memRefs += g_threads[i]->refs;
    PIN_ReleaseLock(&g_threadsLock);

    if (g_dramAccesses > 0 || g_epochId == 0) finishEpoch();
    PIN_ReleaseLock(&g_lock);

    if (g_pagesBin) {
        fclose(g_pagesBin);
        g_pagesBin = NULL;
    }
    if (g_epochCsv.is_open()) g_epochCsv.close();
    if (g_trackCsv.is_open()) g_trackCsv.close();
    writeSummary();
}

INT32 usage() {
    std::cerr << "hotskew -- cache-line-granularity hot-skewness profiler (M5 Fig. 4 / Fig. 10)\n\n"
              << KNOB_BASE::StringKnobSummary() << "\n";
    return -1;
}

}  // namespace

int main(int argc, char* argv[]) {
    PIN_InitSymbols();
    if (PIN_Init(argc, argv)) return usage();

    g_outPrefix = KnobOut.Value();
    g_tag = KnobTag.Value();
    g_useCache = KnobCacheOn.Value() != 0;
    g_countWB = KnobCountWB.Value() != 0;

    const UINT64 M = 1000000ULL;
    g_ffTarget = KnobFastForward.Value() * M;
    g_warmupTarget = KnobWarmup.Value() * M;
    g_lenTarget = KnobLength.Value() * M;
    g_epochTarget = KnobEpoch.Value() * M;
    g_epochInsTarget = KnobEpochIns.Value() * M;
    // A time-proportional window and an access-proportional window are different
    // questions; running both at once would close epochs at whichever fires first
    // and make the result impossible to interpret. -epoch_ins wins outright.
    if (g_epochInsTarget) g_epochTarget = 0;

    memset(g_uniqueWordHist, 0, sizeof(g_uniqueWordHist));
    memset(g_pageAccessHist, 0, sizeof(g_pageAccessHist));

    if (g_useCache) {
        if (!g_llc.init("LLC", KnobL3Size.Value() * 1024, KnobL3Assoc.Value(), 1u << kWordShift)) {
            std::cerr << "[hotskew] LLC geometry gives a non-power-of-two set count; "
                      << "adjust -l3_kb / -l3_assoc\n";
            return 1;
        }
    }

    // If any ROI marker was named, stay disabled until we enter it.
    const bool haveRoi = !KnobRoiRtn.Value().empty() || !KnobRoiBegin.Value().empty();
    g_roiEnabled = !haveRoi;
    g_phase = g_ffTarget ? PHASE_FASTFORWARD : (g_warmupTarget ? PHASE_WARMUP : PHASE_PROFILE);
    g_active = (g_phase != PHASE_FASTFORWARD && g_roiEnabled) ? 1 : 0;

    PIN_InitLock(&g_lock);
    PIN_InitLock(&g_threadsLock);
    g_tlsKey = PIN_CreateThreadDataKey(NULL);

    const string csvPath = g_outPrefix + ".epochs.csv";
    g_epochCsv.open(csvPath.c_str());
    g_epochCsv << "epoch,pages,accesses,mean_unique_words,p_le_4,p_le_8,p_le_16,p_le_32,p_le_48\n";

    g_track = KnobTrack.Value() != 0;
    g_trackWord = KnobTrackWord.Value() != 0;
    g_trackCM = (KnobTrackAlgo.Value() == "cmsketch");
    if (g_track) {
        // Parse the comma-separated budget list.
        std::vector<UINT32> budgets;
        {
            const string& v = KnobTrackN.Value();
            size_t i = 0;
            while (i < v.size()) {
                size_t j = v.find(',', i);
                if (j == string::npos) j = v.size();
                const string tok = v.substr(i, j - i);
                if (!tok.empty()) {
                    UINT32 n = (UINT32)strtoul(tok.c_str(), NULL, 10);
                    if (n) budgets.push_back(n);
                }
                i = j + 1;
            }
        }
        if (budgets.empty()) budgets.push_back(512);
        for (size_t i = 0; i < budgets.size(); ++i) {
            TrackerSlot* t = new TrackerSlot();
            t->n = budgets[i];
            if (g_trackCM) {
                const UINT32 d = KnobTrackDepth.Value() ? KnobTrackDepth.Value() : 1;
                const UINT32 w = t->n / d;
                t->hptCM.init(d, w ? w : 1, KnobTrackK.Value());
                t->hwtCM.init(d, w ? w : 1, KnobTrackK.Value());
            } else {
                t->hpt.init(t->n);
                t->hwt.init(t->n);
            }
            g_slots.push_back(t);
        }
        const string tp = g_outPrefix + ".tracker.csv";
        g_trackCsv.open(tp.c_str());
        g_trackCsv << "epoch,k,n,algo,hpt_access_ratio,hpt_recall,hwt_access_ratio,"
                      "hwt_recall,exact_pages,exact_words\n";
        std::cerr << "[hotskew] tracking " << g_slots.size() << " budget(s), "
                  << (g_trackCM ? "CM-Sketch" : "Space-Saving") << "\n";
    }

    if (KnobDumpPages.Value()) {
        const string binPath = g_outPrefix + ".pages.bin";
        g_pagesBin = fopen(binPath.c_str(), "wb");
        if (!g_pagesBin) std::cerr << "[hotskew] could not open " << binPath << "\n";
    }

    TRACE_AddInstrumentFunction(instrumentTrace, NULL);
    if (haveRoi || !KnobRoiEnd.Value().empty())
        RTN_AddInstrumentFunction(instrumentRoutine, NULL);
    PIN_AddThreadStartFunction(onThreadStart, NULL);
    PIN_AddFiniFunction(onFini, NULL);

    PIN_StartProgram();
    return 0;
}
