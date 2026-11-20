// Three simultaneous streams over identical execution intervals. Histograms are
// kept both conditional on each stream touching a page and on a common page set.
#ifndef HOTSKEW_PAIRED_OBSERVER_HPP
#define HOTSKEW_PAIRED_OBSERVER_HPP
#include <stdint.h>
#include <unordered_map>
#include <ostream>
namespace hotskew {
class PairedObserver {
  public:
    enum Stream { ACCESSES = 0, FILLS = 1, TRAFFIC = 2 };
    struct Masks { uint64_t bits[3] = {0, 0, 0}; };
    typedef std::unordered_map<uint64_t, Masks> Pages;
    Pages epoch, whole;
    uint64_t epochEvents[3] = {}, totalEvents[3] = {};
    uint64_t pooled[3][3][65] = {};
    // Window ladder. Level j holds windows of 2^j consecutive epochs, built by
    // OR-ing two completed level j-1 windows -- exactly the mask a counter left
    // running 2^j times longer would hold. One pass therefore measures every
    // window length from one epoch up to 2^(kLevels-1) epochs, so no window has
    // to be chosen per benchmark after seeing a curve.
    static const unsigned kLevels = 11;
    Pages acc[kLevels];
    unsigned fill[kLevels] = {};
    uint64_t done[kLevels] = {};
    uint64_t ladder[kLevels][3][3][65] = {};
    void carry(const Pages& src, unsigned j) {
        if (j >= kLevels) return;
        for (const auto& item : src) {
            Masks& m = acc[j][item.first];
            for (unsigned s = 0; s < 3; ++s) m.bits[s] |= item.second.bits[s];
        }
        if (++fill[j] < 2) return;
        histograms(acc[j], ladder[j]);
        ++done[j];
        carry(acc[j], j + 1);
        acc[j].clear();
        fill[j] = 0;
    }
    void record(uint64_t line, Stream stream) {
        const uint64_t page = line >> 6, bit = uint64_t(1) << (line & 63);
        epoch[page].bits[stream] |= bit;
        whole[page].bits[stream] |= bit;
        ++epochEvents[stream];
        ++totalEvents[stream];
    }
    bool empty() const { return epoch.empty(); }
    static void histograms(const Pages& pages, uint64_t (&hist)[3][3][65]) {
        for (const auto& item : pages) {
            const Masks& m = item.second;
            for (unsigned s = 0; s < 3; ++s) {
                const unsigned words = __builtin_popcountll(m.bits[s]);
                if (words) ++hist[s][0][words]; // stream-touched pages
                if (m.bits[ACCESSES]) ++hist[s][1][words]; // access-touched pages
                if (m.bits[FILLS]) ++hist[s][2][words]; // fill-touched pages
            }
        }
    }
    static void rows(std::ostream& out, const char* scope, uint64_t id,
                     const uint64_t (&hist)[3][3][65], const uint64_t* events) {
        const char* streams[] = {"accesses", "fills", "traffic"};
        const char* populations[] = {"own", "access_pages", "fill_pages"};
        for (unsigned s = 0; s < 3; ++s)
            for (unsigned p = 0; p < 3; ++p)
                for (unsigned n = 0; n <= 64; ++n)
                    out << scope << ',' << id << ',' << streams[s] << ','
                        << populations[p] << ',' << n << ',' << hist[s][p][n]
                        << ',' << events[s] << '\n';
    }
    void endEpoch(std::ostream& out, uint64_t id) {
        uint64_t hist[3][3][65] = {};
        histograms(epoch, hist);
        rows(out, "epoch", id, hist, epochEvents);
        for (unsigned s = 0; s < 3; ++s)
            for (unsigned p = 0; p < 3; ++p)
                for (unsigned n = 0; n <= 64; ++n) pooled[s][p][n] += hist[s][p][n];
        carry(epoch, 1);
        epoch.clear();
        for (unsigned s = 0; s < 3; ++s) epochEvents[s] = 0;
        out.flush();
    }
    void finish(std::ostream& out, uint64_t epochs) {
        rows(out, "pooled", epochs, pooled, totalEvents);
        uint64_t hist[3][3][65] = {};
        histograms(whole, hist);
        rows(out, "whole", 0, hist, totalEvents);
        // "ladder": complete windows only; the events column carries how many.
        // "tail": the one unfinished window per level, reported separately so
        // the analysis decides whether a short remainder is admissible.
        for (unsigned j = 1; j < kLevels; ++j) {
            const uint64_t n[3] = {done[j], done[j], done[j]};
            if (done[j]) rows(out, "ladder", j, ladder[j], n);
            if (fill[j]) {
                uint64_t tail[3][3][65] = {};
                histograms(acc[j], tail);
                const uint64_t one[3] = {1, 1, 1};
                rows(out, "tail", j, tail, one);
            }
        }
    }
};
}
#endif
