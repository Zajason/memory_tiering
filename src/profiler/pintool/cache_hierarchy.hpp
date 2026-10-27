// Demand stores dirty only L1. Lower levels receive clean read fills and full-line
// dirty writebacks; a writeback miss needs no read-for-ownership from memory.
#ifndef HOTSKEW_CACHE_HIERARCHY_HPP
#define HOTSKEW_CACHE_HIERARCHY_HPP
#include "cache_model.hpp"
namespace hotskew {
struct PrivateResult {
    Outcome eviction;
    Outcome demand;
    bool visitedL2;
};
inline PrivateResult accessPrivate(CacheLevel& l1, CacheLevel& l2,
                                   uint64_t line, AccessType type) {
    PrivateResult r = {{true, false, 0}, {true, false, 0}, false};
    Outcome first = l1.access(line, type);
    if (first.hit) return r;
    r.visitedL2 = true;
    if (first.wroteBack) r.eviction = l2.access(first.wbLineAddr, ACCESS_WRITE);
    r.demand = l2.access(line, ACCESS_READ);
    return r;
}
template<class Record>
void accessShared(CacheLevel& llc, uint64_t line, const PrivateResult& r,
                  Record record) {
    const Outcome outgoing[] = {r.eviction, r.demand};
    for (const Outcome& o : outgoing) {
        if (!o.wroteBack) continue;
        Outcome wb = llc.access(o.wbLineAddr, ACCESS_WRITE);
        if (wb.wroteBack) record(wb.wbLineAddr, true);
    }
    if (!r.demand.hit) {
        Outcome fill = llc.access(line, ACCESS_READ);
        if (fill.wroteBack) record(fill.wbLineAddr, true);
        if (!fill.hit) record(line, false);
    }
}
}
#endif
