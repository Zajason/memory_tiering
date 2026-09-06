// standalone_driver.cpp -- drive the probe from a trace, with no Pin involved.
//
// Two jobs:
//
//  1. A worked example of the simulator integration. Anything that can produce
//     (physical address, is_write) pairs can drive hotskew::Probe; a full-system
//     simulator's device port is one such thing, and so is this file.
//
//  2. A regression test that the counting and tracking code builds and runs outside
//     Pin. That matters because the whole argument for moving to CXLRAMSim is that
//     the *same* structures see physical addresses and kernel traffic there. If they
//     could only be built inside a pintool, that argument would be hollow.
//
// It also self-checks against a stream whose hot set is known by construction. The
// pass condition is not "N bigger than the hot set" -- that is wrong, and getting it
// wrong is instructive.
//
// Space-Saving gives an evicted slot the count min+1, so a long cold tail inflates
// every cold entry to roughly n_cold / N. The hot set survives only while that stays
// below the hot pages' own count:
//
//     N  >  hot_pages + n_cold / hot_hits_per_page
//
// So the tracker size an HPT needs is set by the length of the *cold tail*, not by
// the size of the hot set. With 64 hot pages at 400 hits each and a 100k-page tail,
// 256 entries loses the hot set completely (0.002) while 512 recovers it exactly --
// a 2x change in hardware either side of a threshold that has nothing to do with how
// many pages are hot. That is a real sizing result, and this test asserts it.
//
// Build: make -C src/sim
// Run:   ./src/sim/hotskew_sim --self-test
//        ./src/sim/hotskew_sim --trace <file> [--epoch N] [--budgets 50,128,512]
//
// Trace format: one record per line, "<hex_addr> <R|W>", or pass --binary for
// packed 8-byte little-endian addresses with the low bit as the write flag.

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "hotskew_probe.hpp"

using namespace hotskew;

static std::vector<uint32_t> parseBudgets(const std::string& s) {
    std::vector<uint32_t> out;
    std::stringstream ss(s);
    std::string tok;
    while (std::getline(ss, tok, ',')) {
        if (tok.empty()) continue;
        uint32_t v = (uint32_t)strtoul(tok.c_str(), NULL, 10);
        if (v) out.push_back(v);
    }
    return out;
}

// A stream with a hot set of known size: `hot` pages get most of the traffic, the
// rest is spread thinly. A tracker with N > hot must recover it exactly.
static int selfTest() {
    const uint64_t kHotPages = 64;
    const uint64_t kColdPages = 100000;
    const uint64_t kHotHits = 400;

    ProbeConfig cfg;
    cfg.trackerBudgets = parseBudgets("16,256,512,4096");
    cfg.topK = 64;
    cfg.trackWords = true;
    Probe probe;
    probe.init(cfg);

    uint64_t rng = 0x9E3779B97F4A7C15ULL;
    for (uint64_t i = 0; i < kHotPages * kHotHits; ++i) {
        const uint64_t page = i % kHotPages;
        rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17;
        const uint64_t word = rng % 64;
        probe.onRequest((page << 12) | (word << 6), false);
    }
    for (uint64_t p = 0; p < kColdPages; ++p)
        probe.onRequest(((kHotPages + p) << 12), false);
    probe.endEpoch();

    const std::vector<EpochResult>& r = probe.results();
    if (r.empty()) {
        fprintf(stderr, "FAIL: probe recorded no epochs\n");
        return 1;
    }
    printf("standalone probe self-test  (hot set = %" PRIu64 " pages, %" PRIu64
           " cold pages)\n\n",
           kHotPages, kColdPages);
    // Threshold above which the cold tail can no longer displace the hot set.
    const double kNeeded = (double)kHotPages + (double)kColdPages / (double)kHotHits;
    printf("  cold-tail threshold: N > %.0f  (= hot_pages + n_cold / hits_per_hot_page)\n\n",
           kNeeded);
    printf("  %-10s %-18s %s\n", "budget N", "hpt_access_ratio", "verdict");
    int failures = 0;
    for (size_t b = 0; b < cfg.trackerBudgets.size(); ++b) {
        const uint32_t n = cfg.trackerBudgets[b];
        const double ratio = r[0].hptAccessRatio[b];
        const bool shouldBeExact = ((double)n > kNeeded);
        const char* verdict;
        if (shouldBeExact && ratio < 0.999) {
            verdict = "FAIL (above threshold, expected 1.000)";
            ++failures;
        } else if (shouldBeExact) {
            verdict = "exact, as the threshold predicts";
        } else if (ratio > 0.5) {
            verdict = "FAIL (below threshold, should have degraded)";
            ++failures;
        } else {
            verdict = "degraded, as the threshold predicts";
        }
        printf("  %-10u %-18.4f %s\n", n, ratio, verdict);
    }
    printf("\n  pages seen %" PRIu64 ", accesses %" PRIu64 ", mean unique words %.2f/64\n",
           r[0].pages, r[0].accesses, r[0].meanUniqueWords);
    if (failures) {
        printf("\n%d check(s) failed -- the probe is not usable in a simulator.\n", failures);
        return 1;
    }
    printf("\nall checks passed: the counters and trackers work outside Pin, and the\n"
           "tracker degrades exactly where the cold-tail threshold says it should.\n");
    return 0;
}

int main(int argc, char** argv) {
    std::string tracePath;
    std::string budgets = "50,128,512,2048";
    uint64_t epoch = 10000000;
    uint32_t topK = 128;
    bool binary = false, cm = false, self = false;
    std::string outPrefix = "hotskew_sim";

    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--self-test") self = true;
        else if (a == "--binary") binary = true;
        else if (a == "--cmsketch") cm = true;
        else if (a == "--trace" && i + 1 < argc) tracePath = argv[++i];
        else if (a == "--budgets" && i + 1 < argc) budgets = argv[++i];
        else if (a == "--epoch" && i + 1 < argc) epoch = strtoull(argv[++i], NULL, 10);
        else if (a == "--topk" && i + 1 < argc) topK = (uint32_t)strtoul(argv[++i], NULL, 10);
        else if (a == "-o" && i + 1 < argc) outPrefix = argv[++i];
        else {
            fprintf(stderr,
                    "usage: %s --self-test\n"
                    "       %s --trace <file> [--binary] [--cmsketch]\n"
                    "            [--budgets 50,128,512] [--epoch N] [--topk K] [-o prefix]\n",
                    argv[0], argv[0]);
            return 1;
        }
    }

    if (self || tracePath.empty()) return selfTest();

    ProbeConfig cfg;
    cfg.trackerBudgets = parseBudgets(budgets);
    cfg.topK = topK;
    cfg.useCountMin = cm;
    cfg.epochAccesses = epoch;
    Probe probe;
    probe.init(cfg);

    uint64_t n = 0;
    if (binary) {
        std::ifstream f(tracePath.c_str(), std::ios::binary);
        if (!f) { fprintf(stderr, "cannot open %s\n", tracePath.c_str()); return 1; }
        uint64_t rec;
        while (f.read(reinterpret_cast<char*>(&rec), sizeof(rec))) {
            probe.onRequest(rec & ~1ULL, (rec & 1ULL) != 0);
            ++n;
        }
    } else {
        std::ifstream f(tracePath.c_str());
        if (!f) { fprintf(stderr, "cannot open %s\n", tracePath.c_str()); return 1; }
        std::string addr, rw;
        while (f >> addr >> rw) {
            probe.onRequest(strtoull(addr.c_str(), NULL, 16), rw == "W" || rw == "w");
            ++n;
        }
    }
    probe.endEpoch();
    probe.writeSummary(outPrefix + ".summary.txt");
    printf("processed %" PRIu64 " requests, %zu epochs -> %s.summary.txt\n",
           n, probe.results().size(), outPrefix.c_str());
    return 0;
}
