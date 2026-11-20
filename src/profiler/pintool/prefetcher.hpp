// L2 hardware prefetchers, as Intel documents them for its big cores.
//
// Why this exists: the CXL device counts every read that reaches it, and a
// hardware prefetch is a read like any other. A demand-only cache model
// therefore under-counts the words a real machine touches in a page, which
// biases the Figure 4 curve toward "sparse". M5 does not say prefetchers were
// disabled, so the paper's machine ran with the BIOS default: enabled.
//
// What is modelled, and where each number comes from (Intel 64 and IA-32
// Architectures Optimization Reference Manual, "Data Prefetching"):
//
//   Spatial (adjacent-line) prefetcher
//     "strives to complete every cache line fetched to the L2 cache with the
//      pair line that completes it to a 128-byte aligned chunk"
//     -> on a demand L2 miss for line X, fetch X^1.
//
//   Streamer
//     "monitors read requests from the L1 cache for ascending and descending
//      sequences of addresses"; "prefetched cache lines must be in the same 4K
//      page"; "may issue two prefetch requests on every L2 lookup"; "can run up
//      to 20 lines ahead of the load request"; "detects and maintains up to 32
//      streams"
//     -> one tracked stream per 4 KB page, 32 entries, LRU; two prefetches per
//        L2 lookup once a direction is confirmed; never further than 20 lines
//        ahead and never across the page boundary.
//
// What is NOT in the manual and is therefore our assumption: how many monotone
// requests confirm a stream. kConfirm = 2 means the third request of a monotone
// run is the first to trigger. It is a knob (-pf_confirm) so its influence can
// be reported instead of hidden.
//
// Not modelled: the L1 next-line and IP-stride prefetchers (their fetches are
// largely a subset of what the streamer issues), and the LLC-only far
// prefetches. Both omissions make this model fetch less than real hardware.
#ifndef HOTSKEW_PREFETCHER_HPP
#define HOTSKEW_PREFETCHER_HPP
#include <stdint.h>
namespace hotskew {
class Prefetcher {
  public:
    static const unsigned kStreams = 32;
    static const unsigned kMaxAhead = 20;
    static const unsigned kPerLookup = 2;
    unsigned confirm = 2;

    // Called once per L2 lookup (i.e. per L1 miss). `emit(line)` is invoked for
    // every line the prefetchers would request.
    template<class Emit>
    void onL2Lookup(uint64_t line, bool l2Miss, Emit emit) {
        if (l2Miss) emit(line ^ 1);  // spatial pair

        const uint64_t page = line >> 6;
        Stream* st = 0;
        Stream* victim = &s_[0];
        for (unsigned i = 0; i < kStreams; ++i) {
            if (s_[i].valid && s_[i].page == page) { st = &s_[i]; break; }
            // Prefer a free entry, otherwise the least recently used one.
            if (victim->valid && (!s_[i].valid || s_[i].lru < victim->lru)) victim = &s_[i];
        }
        ++tick_;
        if (!st) {
            victim->valid = true; victim->page = page; victim->last = line;
            victim->front = line; victim->dir = 0; victim->conf = 0;
            victim->lru = tick_;
            return;
        }
        st->lru = tick_;
        if (line == st->last) return;
        const int d = line > st->last ? 1 : -1;
        if (d == st->dir) ++st->conf; else { st->dir = d; st->conf = 1; st->front = line; }
        st->last = line;
        if (st->conf < confirm) return;
        for (unsigned i = 0; i < kPerLookup; ++i) {
            // The prefetch front never falls behind the demand stream.
            uint64_t base = st->front;
            if (d > 0 ? base < line : base > line) base = line;
            const uint64_t next = d > 0 ? base + 1 : base - 1;
            if ((next >> 6) != page) break;
            const uint64_t ahead = d > 0 ? next - line : line - next;
            if (ahead > kMaxAhead) break;
            st->front = next;
            emit(next);
        }
    }

  private:
    struct Stream {
        uint64_t page, last, front, lru;
        int dir;
        unsigned conf;
        bool valid;
        Stream() : page(0), last(0), front(0), lru(0), dir(0), conf(0), valid(false) {}
    };
    Stream s_[kStreams];
    uint64_t tick_ = 0;
};
}
#endif
