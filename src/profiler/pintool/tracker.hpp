// tracker.hpp -- bounded top-K trackers: M5's HPT and HWT.
//
// What these are
// --------------
// PAC and WAC (counter_table.hpp) keep an *exact* count for every page and every
// 64 B word. That is fine for offline profiling but not something you can build into
// a controller: 256 GB of CXL memory at 4 KB granularity is 64M counters.
//
// M5's answer is a bounded top-K tracker -- a fixed number of entries that
// approximates "which are the hottest addresses" without storing a counter per
// address. Their §5.1 evaluates two families and picks from them:
//
//   Space-Saving (Metwally et al.)  a counter-based heavy-hitter algorithm; exact
//                                   identities, bounded over-estimate, N entries
//   Count-Min Sketch               a hash-based sketch; D x W counters plus a small
//                                   CAM holding the K highest estimates
//
// The paper's own comparison ("M5 with Space-saving 50 counter" and "M5 with
// Count-Min Sketch 2K counter" in the artifact scripts) is between these two, so
// both are implemented here.
//
//   HPT = a tracker keyed on the 4 KB page number  (paddr >> 12)
//   HWT = a tracker keyed on the 64 B word address (paddr >> 6)
//
// Why implement them in the pintool rather than offline
// -----------------------------------------------------
// Space-Saving's result depends on the *order* accesses arrive in, and the
// aggregated per-epoch counts in .pages.bin have already thrown that away. The
// tracker has to see the same stream the hardware would, so it lives here, next to
// the exact counters -- which means every run scores the approximation against
// ground truth for free.
//
// This is M5's Figure 8 metric: the access-count ratio of the pages a tracker
// identifies, divided by that of the true top-K.

#ifndef HOTSKEW_TRACKER_HPP
#define HOTSKEW_TRACKER_HPP

#include <stdint.h>
#include <string.h>

#include <algorithm>
#include <unordered_map>
#include <vector>

namespace hotskew {

// ---------------------------------------------------------------- Space-Saving
//
// N entries, each (key, count, error). On a hit, increment. On a miss with space,
// insert at count 1. On a miss when full, evict the *minimum* entry, reuse its slot
// for the new key, and set the new count to min+1 with error = min. That last step
// is what bounds the over-estimate: a key's true count is in [count-error, count].
//
// The minimum is maintained with a binary min-heap keyed on count, plus a hash map
// from key to heap position. Incrementing a count can only push an entry *down* the
// heap, so an update is one sift-down: O(log N) with N in the tens to thousands.
//
// (Metwally's original paper uses a Stream-Summary for O(1). The heap is the
// standard practical simplification and does not change the algorithm's output.)
class SpaceSaving {
  public:
    void init(uint32_t capacity) {
        cap_ = capacity;
        heap_.clear();
        heap_.reserve(cap_);
        pos_.clear();
        pos_.reserve(cap_ * 2);
        evictions_ = 0;
    }

    void reset() {
        heap_.clear();
        pos_.clear();
        evictions_ = 0;
    }

    inline void access(uint64_t key) {
        std::unordered_map<uint64_t, uint32_t>::iterator it = pos_.find(key);
        if (it != pos_.end()) {
            heap_[it->second].count++;
            siftDown(it->second);
            return;
        }
        if (heap_.size() < cap_) {
            Entry e;
            e.key = key;
            e.count = 1;
            e.error = 0;
            heap_.push_back(e);
            pos_[key] = (uint32_t)(heap_.size() - 1);
            siftUp((uint32_t)(heap_.size() - 1));
            return;
        }
        // Full: the heap root is the minimum. Take its slot.
        Entry& root = heap_[0];
        pos_.erase(root.key);
        root.error = root.count;  // the new key may have been seen up to this often
        root.count = root.count + 1;
        root.key = key;
        pos_[key] = 0;
        siftDown(0);
        ++evictions_;
    }

    // The k keys with the highest estimated counts.
    void topK(uint32_t k, std::vector<uint64_t>& out) const {
        out.clear();
        std::vector<const Entry*> v;
        v.reserve(heap_.size());
        for (size_t i = 0; i < heap_.size(); ++i) v.push_back(&heap_[i]);
        const size_t n = std::min((size_t)k, v.size());
        std::partial_sort(v.begin(), v.begin() + n, v.end(), byCountDesc);
        out.reserve(n);
        for (size_t i = 0; i < n; ++i) out.push_back(v[i]->key);
    }

    bool contains(uint64_t key) const { return pos_.find(key) != pos_.end(); }
    size_t size() const { return heap_.size(); }
    uint64_t evictions() const { return evictions_; }
    uint32_t capacity() const { return cap_; }

    // Storage a hardware implementation would need, in bits: each entry holds a tag
    // and a counter. M5 sizes the tag by the address space being tracked.
    uint64_t bitsPerEntry(uint32_t tagBits, uint32_t counterBits) const {
        return (uint64_t)tagBits + counterBits;
    }

  private:
    struct Entry {
        uint64_t key;
        uint64_t count;
        uint64_t error;
    };

    static bool byCountDesc(const Entry* a, const Entry* b) { return a->count > b->count; }

    void swapAt(uint32_t i, uint32_t j) {
        std::swap(heap_[i], heap_[j]);
        pos_[heap_[i].key] = i;
        pos_[heap_[j].key] = j;
    }

    void siftUp(uint32_t i) {
        while (i > 0) {
            uint32_t p = (i - 1) / 2;
            if (heap_[p].count <= heap_[i].count) break;
            swapAt(i, p);
            i = p;
        }
    }

    void siftDown(uint32_t i) {
        for (;;) {
            uint32_t l = 2 * i + 1, r = l + 1, m = i;
            if (l < heap_.size() && heap_[l].count < heap_[m].count) m = l;
            if (r < heap_.size() && heap_[r].count < heap_[m].count) m = r;
            if (m == i) break;
            swapAt(i, m);
            i = m;
        }
    }

    uint32_t cap_ = 0;
    std::vector<Entry> heap_;
    std::unordered_map<uint64_t, uint32_t> pos_;
    uint64_t evictions_ = 0;
};

// --------------------------------------------------------------- Count-Min + CAM
//
// D rows of W counters. A key hashes to one counter per row; its estimate is the
// minimum of those D counters, which can over-estimate (hash collisions) but never
// under-estimate. A small CAM of K entries holds the highest estimates seen.
//
// The trade against Space-Saving is the one M5 describes: the sketch stores counts
// for *all* addresses in a compact array and needs only one SRAM access per lookup
// (pipelineable), whereas Space-Saving must search all its CAM entries in parallel
// but returns exact identities with no collision noise.
class CountMinTopK {
  public:
    void init(uint32_t depth, uint32_t width, uint32_t k) {
        d_ = depth;
        w_ = width;
        k_ = k;
        counters_.assign((size_t)d_ * w_, 0);
        cam_.clear();
        cam_.reserve(k_);
    }

    void reset() {
        std::fill(counters_.begin(), counters_.end(), 0);
        cam_.clear();
    }

    inline void access(uint64_t key) {
        uint64_t est = UINT64_MAX;
        for (uint32_t r = 0; r < d_; ++r) {
            uint32_t idx = (uint32_t)(hash(key, r) % w_);
            uint64_t& c = counters_[(size_t)r * w_ + idx];
            ++c;
            if (c < est) est = c;
        }
        offerToCam(key, est);
    }

    void topK(uint32_t k, std::vector<uint64_t>& out) const {
        out.clear();
        std::vector<CamEntry> v(cam_);
        const size_t n = std::min((size_t)k, v.size());
        std::partial_sort(v.begin(), v.begin() + n, v.end(), byEstDesc);
        out.reserve(n);
        for (size_t i = 0; i < n; ++i) out.push_back(v[i].key);
    }

    size_t counterCount() const { return counters_.size(); }

  private:
    struct CamEntry {
        uint64_t key;
        uint64_t est;
    };
    static bool byEstDesc(const CamEntry& a, const CamEntry& b) { return a.est > b.est; }

    // Two independent 64-bit mixers, salted per row. Cheap and good enough; a real
    // implementation would use the bitwise AND-of-seed scheme NeoMem describes.
    static inline uint64_t hash(uint64_t x, uint32_t seed) {
        x += 0x9E3779B97F4A7C15ULL * (seed + 1);
        x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
        x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
        return x ^ (x >> 31);
    }

    inline void offerToCam(uint64_t key, uint64_t est) {
        for (size_t i = 0; i < cam_.size(); ++i) {
            if (cam_[i].key == key) {
                cam_[i].est = est;
                return;
            }
        }
        if (cam_.size() < k_) {
            CamEntry e = {key, est};
            cam_.push_back(e);
            return;
        }
        size_t minIdx = 0;
        for (size_t i = 1; i < cam_.size(); ++i)
            if (cam_[i].est < cam_[minIdx].est) minIdx = i;
        if (est > cam_[minIdx].est) {
            cam_[minIdx].key = key;
            cam_[minIdx].est = est;
        }
    }

    uint32_t d_ = 0, w_ = 0, k_ = 0;
    std::vector<uint64_t> counters_;
    std::vector<CamEntry> cam_;
};

// ------------------------------------------------------------------- scoring
//
// M5's Figure 8 metric. Given the tracker's chosen top-K and the *exact* counts, the
// access-count ratio is
//
//     sum of exact counts of the K pages the tracker picked
//     ----------------------------------------------------
//     sum of exact counts of the true top-K pages
//
// 1.0 means the tracker picked a set as hot as the best possible set. It is a fairer
// measure than set overlap, because picking a different page with the same access
// count costs nothing in practice.
struct TrackerScore {
    double accessCountRatio = 0.0;  // M5 Figure 8
    double recall = 0.0;            // |picked n true| / K, for reference
    uint64_t pickedAccesses = 0;
    uint64_t idealAccesses = 0;
    uint32_t k = 0;
};

// `exact` maps key -> true access count for the epoch.
inline TrackerScore scoreTopK(const std::vector<uint64_t>& picked,
                              const std::unordered_map<uint64_t, uint64_t>& exact,
                              uint32_t k) {
    TrackerScore s;
    s.k = k;

    std::vector<uint64_t> counts;
    counts.reserve(exact.size());
    for (std::unordered_map<uint64_t, uint64_t>::const_iterator it = exact.begin();
         it != exact.end(); ++it)
        counts.push_back(it->second);
    const size_t n = std::min((size_t)k, counts.size());
    if (n == 0) return s;
    std::partial_sort(counts.begin(), counts.begin() + n, counts.end(),
                      std::greater<uint64_t>());
    for (size_t i = 0; i < n; ++i) s.idealAccesses += counts[i];

    // Threshold for "would have been in the true top-K", for the recall figure.
    const uint64_t threshold = counts[n - 1];
    uint64_t hits = 0;
    for (size_t i = 0; i < picked.size() && i < k; ++i) {
        std::unordered_map<uint64_t, uint64_t>::const_iterator it = exact.find(picked[i]);
        if (it == exact.end()) continue;
        s.pickedAccesses += it->second;
        if (it->second >= threshold) ++hits;
    }
    s.accessCountRatio = s.idealAccesses ? (double)s.pickedAccesses / (double)s.idealAccesses : 0.0;
    s.recall = k ? (double)hits / (double)k : 0.0;
    return s;
}

}  // namespace hotskew

#endif  // HOTSKEW_TRACKER_HPP
