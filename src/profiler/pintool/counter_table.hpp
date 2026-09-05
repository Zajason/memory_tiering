// counter_table.hpp -- software model of M5's PAC and WAC counter arrays.
//
// M5 (ASPLOS'25, Sec. 3) puts two counter arrays in the CXL controller:
//
//   PAC (Page Access Counter): one L-bit counter per 4 KB page, indexed by
//        PA[47:12]. Answers "how hot is this page?"        -> the paper's Figure 10.
//   WAC (Word Access Counter): one 4-bit counter per 64 B word, indexed by
//        PA[47:6]. Answers "how much OF the page is hot?"  -> the paper's Figure 4.
//
// We keep both in one structure, because a page's PAC value is just the sum of its
// 64 WAC values, and holding them together makes the per-page density query -- the
// whole point of the exercise -- a single lookup.
//
// Layout
// ------
// Address space is sparse, so a flat array is out. We use a two-level scheme keyed
// on 2 MB regions:
//
//     unordered_map<region = addr >> 21>  ->  Region { PageRec page[512]; }
//
// One hash lookup per 2 MB of address space, then a direct index. A one-entry cache
// of the last region turns the common case (consecutive accesses inside one region)
// into a compare-and-branch. That matters: this is on the path of every DRAM access.
//
// Counter widths
// --------------
// WAC uses 4-bit counters in hardware; we use 16-bit and record saturation
// separately, so that we can report how often a 4-bit counter *would* have
// saturated. Under-counting a hot word does not change whether it is "touched"
// (Figure 4 only asks touched/not-touched), but it does change Figure 10, so we
// keep the extra bits and let the analysis scripts model narrower counters if asked.

#ifndef HOTSKEW_COUNTER_TABLE_HPP
#define HOTSKEW_COUNTER_TABLE_HPP

#include <stdint.h>
#include <string.h>
#include <vector>
#include <unordered_map>

namespace hotskew {

static const uint32_t kPageShift = 12;  // 4 KB pages
static const uint32_t kWordShift = 6;   // 64 B words (== cache line)
static const uint32_t kWordsPerPage = 1u << (kPageShift - kWordShift);  // 64
static const uint32_t kRegionShift = 21;  // 2 MB grouping for the radix level
static const uint32_t kPagesPerRegion = 1u << (kRegionShift - kPageShift);  // 512

// Per-4KB-page record. 64 word counters + summary. 160 bytes.
struct PageRec {
    uint16_t word[kWordsPerPage];  // WAC: accesses to each 64 B word
    uint64_t reads;                // PAC, split by direction
    uint64_t writes;
    uint64_t touchedMask;          // bit w set iff word[w] > 0; popcount = unique words
};

struct Region {
    PageRec page[kPagesPerRegion];
};

class CounterTable {
  public:
    CounterTable() : lastRegionId_(~0ULL), lastRegion_(0), totalAccesses_(0), wacSaturations_(0) {}

    ~CounterTable() {
        for (size_t i = 0; i < arena_.size(); ++i) delete arena_[i];
    }

    // Record one DRAM access to a 64 B word. `lineAddr` is a *line number*
    // (byte address >> 6), matching what the cache model hands us.
    inline void record(uint64_t lineAddr, bool isWrite) {
        const uint64_t byteAddr = lineAddr << kWordShift;
        const uint64_t regionId = byteAddr >> kRegionShift;

        Region* r = lastRegion_;
        if (regionId != lastRegionId_) {
            r = lookupRegion(regionId);
            lastRegionId_ = regionId;
            lastRegion_ = r;
        }

        const uint32_t pageIdx = (uint32_t)((byteAddr >> kPageShift) & (kPagesPerRegion - 1));
        const uint32_t wordIdx = (uint32_t)((byteAddr >> kWordShift) & (kWordsPerPage - 1));

        PageRec& p = r->page[pageIdx];
        if (p.word[wordIdx] == 0xFFFF) {
            ++wacSaturations_;
        } else {
            ++p.word[wordIdx];
        }
        p.touchedMask |= (1ULL << wordIdx);
        if (isWrite) ++p.writes; else ++p.reads;
        ++totalAccesses_;
    }

    // Walk every page that saw at least one access. `fn(pageNumber, PageRec&)`.
    template <typename F>
    void forEachTouchedPage(F fn) const {
        for (std::unordered_map<uint64_t, Region*>::const_iterator it = regions_.begin();
             it != regions_.end(); ++it) {
            const Region* r = it->second;
            for (uint32_t i = 0; i < kPagesPerRegion; ++i) {
                const PageRec& p = r->page[i];
                if (p.touchedMask == 0) continue;
                fn((it->first << (kRegionShift - kPageShift)) | i, p);
            }
        }
    }

    // Zero the counters but keep the allocated regions, so that a new epoch does not
    // pay to re-allocate. Epochs are how we avoid the "run long enough and every page
    // looks dense" artefact -- see docs/methodology.md.
    void resetCounters() {
        for (size_t i = 0; i < arena_.size(); ++i) memset(arena_[i], 0, sizeof(Region));
        totalAccesses_ = 0;
        wacSaturations_ = 0;
        lastRegionId_ = ~0ULL;
        lastRegion_ = 0;
    }

    uint64_t totalAccesses() const { return totalAccesses_; }
    uint64_t wacSaturations() const { return wacSaturations_; }
    size_t regionCount() const { return regions_.size(); }
    uint64_t bytesResident() const { return (uint64_t)arena_.size() * sizeof(Region); }

  private:
    Region* lookupRegion(uint64_t regionId) {
        std::unordered_map<uint64_t, Region*>::iterator it = regions_.find(regionId);
        if (it != regions_.end()) return it->second;
        Region* r = new Region();
        memset(r, 0, sizeof(Region));
        arena_.push_back(r);
        regions_[regionId] = r;
        return r;
    }

    std::unordered_map<uint64_t, Region*> regions_;
    std::vector<Region*> arena_;

    uint64_t lastRegionId_;
    Region* lastRegion_;

    uint64_t totalAccesses_;
    uint64_t wacSaturations_;
};

}  // namespace hotskew

#endif  // HOTSKEW_COUNTER_TABLE_HPP
