// cache_model.hpp -- minimal set-associative cache hierarchy for trace filtering.
//
// Why this exists at all
// ----------------------
// M5's Page Access Counter (PAC) and Word Access Counter (WAC) sit inside the CXL
// controller and "snoop every memory access address (PA[47:6]) from the CXL IP to
// the MCs" (M5, ASPLOS'25, Sec. 3). That stream is the *post-LLC* stream: anything
// the CPU caches absorb never reaches the device and is never counted.
//
// A Pin memory-reference tool sees the *architectural* stream instead -- every load
// and store the program executes, before any cache filtering. The two distributions
// are not the same, and the difference is exactly the thing that decides whether a
// page looks dense or sparse. The M5 authors call this out as the reason they did
// not use Pin (Sec. 3, "Limitations of current approaches").
//
// So we put the cache hierarchy back. This header models L1d/L2/LLC as a cascade of
// writeback, write-allocate, LRU set-associative caches; whatever falls out the
// bottom is our stand-in for the CXL request stream.
//
// Modelling choices, stated plainly
// ---------------------------------
//   * Non-inclusive by default (matches Sapphire Rapids' L3). Levels are modelled as
//     independent filters: a miss at level N queries level N+1. There are no
//     back-invalidations from LLC to L1/L2. Turning on `inclusive` adds them.
//   * Writeback + write-allocate. A store that misses fills the line and marks it
//     dirty; evicting a dirty line generates a write to the next level down.
//   * True LRU (not tree-pseudo-LRU). Cheaper to reason about than to defend an
//     approximation, and the associativities here are small.
//   * No coherence traffic between per-core L1/L2 copies. Documented in
//     docs/methodology.md as a known deviation; it matters only for shared,
//     write-heavy lines in multithreaded runs.
//   * No prefetchers. Hardware prefetch would *increase* the number of words touched
//     per page (adjacent-line and stream prefetchers pull in neighbours), so
//     omitting it makes our sparsity numbers a conservative upper bound on density
//     -- i.e. it biases against our own conclusion, which is the safe direction.
//
// Everything here is single-threaded-safe only; the caller serialises shared levels.

#ifndef HOTSKEW_CACHE_MODEL_HPP
#define HOTSKEW_CACHE_MODEL_HPP

#include <stdint.h>
#include <string.h>
#include <vector>
#include <string>

namespace hotskew {

enum AccessType { ACCESS_READ = 0, ACCESS_WRITE = 1 };

// What a level hands down to the next one.
struct Outcome {
    bool hit;             // request was satisfied at this level
    bool wroteBack;       // eviction produced a dirty writeback
    uint64_t wbLineAddr;  // line address of that writeback (valid iff wroteBack)
};

// One set-associative level. Addresses are line-granular *line numbers*
// (byte address >> lineShift), never byte addresses -- keeps the arithmetic honest.
class CacheLevel {
  public:
    CacheLevel() : numSets_(0), assoc_(0), lineShift_(6), setBits_(0), setMask_(0), clock_(0) {}

    // The number of sets must come out a power of two: sizeBytes / (lineBytes * assoc).
    // Real geometries cooperate -- e.g. SPR's 60 MB 15-way L3 gives exactly 65536 sets.
    // Returns false if the geometry is not representable, so main() can complain.
    bool init(const std::string& name, uint64_t sizeBytes, uint32_t assoc, uint32_t lineBytes) {
        name_ = name;
        assoc_ = assoc;
        lineShift_ = log2u(lineBytes);
        uint64_t sets = sizeBytes / (lineBytes * (uint64_t)assoc);
        if (sets == 0 || (sets & (sets - 1)) != 0) return false;
        numSets_ = static_cast<uint32_t>(sets);
        setBits_ = log2u(numSets_);
        setMask_ = numSets_ - 1;
        tag_.assign((size_t)numSets_ * assoc_, 0);
        stamp_.assign((size_t)numSets_ * assoc_, 0);
        valid_.assign((size_t)numSets_ * assoc_, 0);
        dirty_.assign((size_t)numSets_ * assoc_, 0);
        clock_ = 1;
        hits_ = misses_ = writebacks_ = 0;
        return true;
    }

    bool enabled() const { return numSets_ != 0; }
    const std::string& name() const { return name_; }
    uint32_t lineShift() const { return lineShift_; }

    uint64_t hits() const { return hits_; }
    uint64_t misses() const { return misses_; }
    uint64_t writebacks() const { return writebacks_; }
    uint64_t sizeBytes() const { return (uint64_t)numSets_ * assoc_ << lineShift_; }
    uint32_t assoc() const { return assoc_; }
    uint32_t numSets() const { return numSets_; }

    // Access one cache line. `lineAddr` is a line number.
    Outcome access(uint64_t lineAddr, AccessType type) {
        Outcome out;
        out.hit = false;
        out.wroteBack = false;
        out.wbLineAddr = 0;

        const uint32_t set = (uint32_t)(lineAddr & setMask_);
        const size_t base = (size_t)set * assoc_;
        const uint64_t tag = lineAddr >> setBits_;

        // Probe.
        for (uint32_t w = 0; w < assoc_; ++w) {
            if (valid_[base + w] && tag_[base + w] == tag) {
                stamp_[base + w] = clock_++;
                if (type == ACCESS_WRITE) dirty_[base + w] = 1;
                out.hit = true;
                ++hits_;
                return out;
            }
        }

        ++misses_;

        // Pick a victim: first invalid way, else least-recently-used.
        uint32_t victim = 0;
        bool foundFree = false;
        for (uint32_t w = 0; w < assoc_; ++w) {
            if (!valid_[base + w]) {
                victim = w;
                foundFree = true;
                break;
            }
        }
        if (!foundFree) {
            uint64_t oldest = ~0ULL;
            for (uint32_t w = 0; w < assoc_; ++w) {
                if (stamp_[base + w] < oldest) {
                    oldest = stamp_[base + w];
                    victim = w;
                }
            }
            if (dirty_[base + victim]) {
                out.wroteBack = true;
                out.wbLineAddr = (tag_[base + victim] << setBits_) | set;
                ++writebacks_;
            }
        }

        // Fill (write-allocate).
        tag_[base + victim] = tag;
        valid_[base + victim] = 1;
        dirty_[base + victim] = (type == ACCESS_WRITE) ? 1 : 0;
        stamp_[base + victim] = clock_++;
        return out;
    }

    // Used only when modelling an inclusive LLC: drop a line if present.
    // Returns true if the dropped line was dirty (caller must write it back).
    bool invalidate(uint64_t lineAddr) {
        if (!enabled()) return false;
        const uint32_t set = (uint32_t)(lineAddr & setMask_);
        const size_t base = (size_t)set * assoc_;
        const uint64_t tag = lineAddr >> setBits_;
        for (uint32_t w = 0; w < assoc_; ++w) {
            if (valid_[base + w] && tag_[base + w] == tag) {
                bool wasDirty = dirty_[base + w] != 0;
                valid_[base + w] = 0;
                dirty_[base + w] = 0;
                return wasDirty;
            }
        }
        return false;
    }

    void resetStats() { hits_ = misses_ = writebacks_ = 0; }

  private:
    static uint32_t log2u(uint64_t v) {
        uint32_t r = 0;
        while (v > 1) {
            v >>= 1;
            ++r;
        }
        return r;
    }

    std::string name_;
    uint32_t numSets_;
    uint32_t assoc_;
    uint32_t lineShift_;
    uint32_t setBits_;
    uint64_t setMask_;
    uint64_t clock_;

    std::vector<uint64_t> tag_;
    std::vector<uint64_t> stamp_;
    std::vector<uint8_t> valid_;
    std::vector<uint8_t> dirty_;

    uint64_t hits_ = 0, misses_ = 0, writebacks_ = 0;
};

// Geometry of one level, filled from command-line knobs.
struct LevelConfig {
    uint64_t sizeBytes = 0;  // 0 disables the level
    uint32_t assoc = 8;
};

}  // namespace hotskew

#endif  // HOTSKEW_CACHE_MODEL_HPP
