#include "../pintool/cache_hierarchy.hpp"
#include "../pintool/paired_observer.hpp"
#include "../pintool/counter_table.hpp"
#include "../../sim/hotskew_probe.hpp"
#include <unistd.h>
#include <cassert>
#include <iostream>
#include <sstream>
#include <utility>
#include <vector>
using namespace hotskew;
int main() {
    CacheLevel l1, l2, llc;
    assert(!l1.init("bad", 64, 0, 64));
    assert(!l1.init("bad", 65, 1, 64));
    assert(!l1.init("bad", 64, 1, 0));
    assert(l1.init("l1", 128, 2, 64));
    assert(l2.init("l2", 64, 1, 64));
    assert(llc.init("llc", 64, 1, 64));
    l1.access(0, ACCESS_WRITE); l1.access(1, ACCESS_WRITE);
    l2.access(2, ACCESS_WRITE); llc.access(4, ACCESS_WRITE);
    PrivateResult r = accessPrivate(l1, l2, 3, ACCESS_READ);
    assert(r.eviction.wroteBack && r.eviction.wbLineAddr == 2);
    assert(r.demand.wroteBack && r.demand.wbLineAddr == 0);
    std::vector<std::pair<uint64_t, bool>> events;
    accessShared(llc, 3, r, [&](uint64_t line, bool write) { events.emplace_back(line, write); });
    const std::vector<std::pair<uint64_t, bool>> expected = {{4,true},{2,true},{0,true},{3,false}};
    assert(events == expected);

    // A store fill dirties L1 only. Clean lower copies cannot write back early.
    l1.init("l1", 128, 2, 64); l2.init("l2", 64, 1, 64); llc.init("llc", 64, 1, 64);
    events.clear();
    for (uint64_t line = 0; line < 2; ++line) {
        auto result = accessPrivate(l1, l2, line, ACCESS_WRITE);
        accessShared(llc, line, result, [&](uint64_t a, bool w) { events.emplace_back(a,w); });
    }
    assert(events.size() == 2 && !events[0].second && !events[1].second);
    assert(l2.writebacks() == 0 && llc.writebacks() == 0);
    events.clear();
    accessShared(llc, 0, accessPrivate(l1, l2, 0, ACCESS_READ),
                 [&](uint64_t a, bool w) { events.emplace_back(a,w); });
    assert(events.empty()); // L1 hit cannot invent a DRAM access.

    // Same execution interval, but own-population and common-population CDFs differ.
    PairedObserver p;
    p.record(0, PairedObserver::ACCESSES);
    p.record(1, PairedObserver::ACCESSES);
    p.record(64, PairedObserver::ACCESSES);
    p.record(0, PairedObserver::FILLS);
    p.record(0, PairedObserver::TRAFFIC);
    p.record(128, PairedObserver::TRAFFIC); // writeback of an older page
    uint64_t hist[3][3][65] = {};
    PairedObserver::histograms(p.epoch, hist);
    assert(hist[0][0][2] == 1 && hist[0][0][1] == 1);
    assert(hist[1][0][1] == 1 && hist[1][1][0] == 1);
    assert(hist[2][0][1] == 2 && hist[2][1][0] == 1);
    std::ostringstream csv;
    p.endEpoch(csv, 0);
    assert(p.empty() && p.whole.size() == 3);
    p.record(2, PairedObserver::ACCESSES);
    p.endEpoch(csv, 1);
    assert(p.pooled[0][0][1] == 2 && p.pooled[0][0][2] == 1);
    uint64_t whole[3][3][65] = {};
    PairedObserver::histograms(p.whole, whole);
    assert(whole[0][0][3] == 1); // union, not sum of epoch distinct counts
    CounterTable counts;
    for (unsigned i = 0; i < 65537; ++i) counts.record(0, false);
    assert(counts.wacSaturations() == 2 && counts.totalAccesses() == 65537);
    Probe probe;
    ProbeConfig cfg; cfg.trackerBudgets = {2}; cfg.trackWords = false;
    probe.init(cfg);
    probe.onRequest(0, false); probe.endEpoch();
    for (unsigned line = 64; line < 192; ++line) probe.onRequest(line*64, false);
    probe.endEpoch();
    const std::string file = "/tmp/hotskew-probe-audit-" + std::to_string(getpid());
    probe.writeSummaryTo(file);
    std::ifstream report(file);
    std::string text((std::istreambuf_iterator<char>(report)), std::istreambuf_iterator<char>());
    assert(text.find("43.000 / 64") != std::string::npos);
    std::remove(file.c_str());
    probe.onRequest(0, false);
    probe.init(cfg);
    probe.endEpoch();
    assert(probe.results().empty());
    probe.onRequest(60, false, 8);
    probe.endEpoch();
    assert(probe.results()[0].accesses == 2 && probe.results()[0].meanUniqueWords == 2);
    std::cout << "PASS: dirty evictions, clean fills, hits, geometry, paired populations, union, saturation\n";
}
