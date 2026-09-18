// hotskew_probe.hpp -- Deliverable 3: the simulator-facing interface.
//
// Status of the target simulator
// ------------------------------
// CXLRAMSim v1.0 is **not released**. The paper (arXiv 2603.29483) says "We plan to
// open-source and integrate our work into gem5 mainstream repository", and no public
// repository exists as of this writing. So this cannot be a port; it is the thing
// that makes the port a small job when the simulator lands.
//
// What this is
// ------------
// One header with no dependency on Pin, on the benchmark harness, or on anything
// else in this repository except the two data structures that do the work:
//
//     counter_table.hpp   exact per-page and per-64B-word counts  (PAC / WAC)
//     tracker.hpp         bounded top-K trackers                  (HPT / HWT)
//
// A simulator hooks it by calling exactly one function per memory request:
//
//     probe.onRequest(physAddr, isWrite);
//
// and one function per measurement interval:
//
//     probe.endEpoch();
//
// That is the whole contract. Everything the Pin tool does with these structures is
// reachable through it.
//
// Why the interface is this small
// -------------------------------
// Because the hard part is not the counters, it is *where they sit*. In the Pin tool
// they sit behind a modelled cache hierarchy, and they are blind to kernel-side
// traffic (docs/methodology.md §3b). In a full-system simulator they sit on the CXL
// device's request path and see everything -- application, kernel, page-fault
// zeroing, DMA -- with real physical addresses. That is the whole reason to move
// there, and it requires no change to the counting code at all.
//
// Integration sketch, gem5
// ------------------------
// CXLRAMSim models a CXL endpoint as a gem5 MemObject on the IOBus. The natural hook
// is the port that receives M2S requests:
//
//     class CxlMemory : public SimObject {
//         hotskew::Probe probe;
//         bool recvTimingReq(PacketPtr pkt) override {
//             probe.onRequest(pkt->getAddr(), pkt->isWrite());   // <-- one line
//             return next_port.sendTimingReq(pkt);
//         }
//         void regStats() override { ...; probe.writeSummary(name() + ".hotskew"); }
//     };
//
// and endEpoch() from an existing periodic event, or from the tick at which the
// simulator's own stat dump fires.
//
// Anything that can produce (address, is_write) pairs can drive it. src/sim/
// standalone_driver.cpp does exactly that from a text or binary trace, which is both
// a worked example and the regression test that this header compiles and runs
// outside Pin.

#ifndef HOTSKEW_PROBE_HPP
#define HOTSKEW_PROBE_HPP

#include <stdint.h>

#include <fstream>
#include <iomanip>
#include <string>
#include <unordered_map>
#include <vector>

#include "../profiler/pintool/counter_table.hpp"
#include "../profiler/pintool/tracker.hpp"

namespace hotskew {

struct ProbeConfig {
    // Bounded tracker budgets to evaluate. Each is fed the same stream, so the whole
    // accuracy-vs-hardware-cost curve costs one simulation.
    std::vector<uint32_t> trackerBudgets;
    uint32_t topK = 128;         // how many hot pages the tracker reports
    bool useCountMin = false;    // false = Space-Saving, true = CM-Sketch
    uint32_t cmDepth = 2;        // CM-Sketch rows (NeoMem uses 2)
    bool trackWords = true;      // also run the HWT
    uint64_t epochAccesses = 0;  // auto-close an epoch every N requests; 0 = manual
};

// Per-epoch results, so a simulator can log them as it goes rather than only at end.
struct EpochResult {
    uint32_t epoch = 0;
    uint64_t pages = 0;
    uint64_t accesses = 0;
    double meanUniqueWords = 0.0;
    // Indexed the same as ProbeConfig::trackerBudgets.
    std::vector<double> hptAccessRatio;
    std::vector<double> hwtAccessRatio;
    // uniqueHist[w] = pages touching exactly w distinct 64B words this epoch.
    // This is what Figure 4 is a CDF of; without it the summary cannot be
    // compared against M5 at all.
    std::vector<uint64_t> uniqueHist = std::vector<uint64_t>(kWordsPerPage + 1, 0);
};

class Probe {
  public:
    void init(const ProbeConfig& cfg) {
        cfg_ = cfg;
        if (cfg_.trackerBudgets.empty()) cfg_.trackerBudgets.push_back(512);
        slots_.clear();
        for (size_t i = 0; i < cfg_.trackerBudgets.size(); ++i) {
            Slot s;
            s.n = cfg_.trackerBudgets[i];
            if (cfg_.useCountMin) {
                const uint32_t d = cfg_.cmDepth ? cfg_.cmDepth : 1;
                const uint32_t w = s.n / d ? s.n / d : 1;
                s.hptCM.init(d, w, cfg_.topK);
                s.hwtCM.init(d, w, cfg_.topK);
            } else {
                s.hpt.init(s.n);
                s.hwt.init(s.n);
            }
            slots_.push_back(s);
        }
        epoch_ = 0;
        sinceEpoch_ = 0;
        results_.clear();
    }

    // One CXL memory request. `physAddr` is a byte address; the simulator supplies a
    // real physical address, which is the point of running here rather than in Pin.
    inline void onRequest(uint64_t physAddr, bool isWrite) {
        const uint64_t line = physAddr >> kWordShift;
        counters_.record(line, isWrite);

        const uint64_t page = line >> (kPageShift - kWordShift);
        for (size_t i = 0; i < slots_.size(); ++i) {
            Slot& s = slots_[i];
            if (cfg_.useCountMin) {
                s.hptCM.access(page);
                if (cfg_.trackWords) s.hwtCM.access(line);
            } else {
                s.hpt.access(page);
                if (cfg_.trackWords && s.hpt.contains(page)) s.hwt.access(line);
            }
        }

        if (cfg_.epochAccesses && ++sinceEpoch_ >= cfg_.epochAccesses) endEpoch();
    }

    // Close the measurement window: score the trackers against the exact counts,
    // record the epoch, and reset both.
    void endEpoch() {
        EpochResult r;
        r.epoch = epoch_;

        std::unordered_map<uint64_t, uint64_t> exactPages, exactWords;
        uint64_t words = 0;
        counters_.forEachTouchedPage([&](uint64_t pageNo, const PageRec& p) {
            const uint64_t tot = p.reads + p.writes;
            exactPages[pageNo] = tot;
            r.pages++;
            r.accesses += tot;
            const uint32_t uw = (uint32_t)__builtin_popcountll(p.touchedMask);
            words += uw;
            ++r.uniqueHist[uw];
            if (cfg_.trackWords) {
                for (uint32_t w = 0; w < kWordsPerPage; ++w)
                    if (p.word[w])
                        exactWords[(pageNo << (kPageShift - kWordShift)) | w] = p.word[w];
            }
        });
        if (r.pages == 0) return;  // nothing happened; do not burn an epoch id
        r.meanUniqueWords = (double)words / (double)r.pages;

        for (size_t i = 0; i < slots_.size(); ++i) {
            Slot& s = slots_[i];
            std::vector<uint64_t> picked;
            if (cfg_.useCountMin) s.hptCM.topK(cfg_.topK, picked);
            else s.hpt.topK(cfg_.topK, picked);
            r.hptAccessRatio.push_back(scoreTopK(picked, exactPages, cfg_.topK).accessCountRatio);

            double hw = 0.0;
            if (cfg_.trackWords) {
                std::vector<uint64_t> pw;
                if (cfg_.useCountMin) s.hwtCM.topK(cfg_.topK, pw);
                else s.hwt.topK(cfg_.topK, pw);
                hw = scoreTopK(pw, exactWords, cfg_.topK).accessCountRatio;
            }
            r.hwtAccessRatio.push_back(hw);

            if (cfg_.useCountMin) { s.hptCM.reset(); s.hwtCM.reset(); }
            else { s.hpt.reset(); s.hwt.reset(); }
        }

        results_.push_back(r);
        counters_.resetCounters();
        ++epoch_;
        sinceEpoch_ = 0;
    }

    const std::vector<EpochResult>& results() const { return results_; }
    const CounterTable& counters() const { return counters_; }

    // Same shape as the pintool's summary, so the analysis scripts in src/analysis/
    // read simulator output without modification.
    void writeSummary(const std::string& path) const {
        std::ofstream f(path.c_str());
        f << "# hotskew probe summary (simulator-driven)\n";
        f << "epochs             " << results_.size() << "\n";
        if (results_.empty()) {
            f << "STATUS             NO DATA\n";
            return;
        }
        uint64_t pages = 0, acc = 0;
        double mu = 0.0;
        for (size_t i = 0; i < results_.size(); ++i) {
            pages += results_[i].pages;
            acc += results_[i].accesses;
            mu += results_[i].meanUniqueWords;
        }
        f << "page_observations  " << pages << "\n";
        f << "dram_accesses      " << acc << "\n";
        f << "mean_unique_words  " << std::fixed << std::setprecision(3)
          << (mu / results_.size()) << " / 64\n";
        // Section name and "words,count" shape must match what the pintool
        // writes, because src/analysis/hotskew.py:load_summary() keys off this
        // exact header to build the Figure 4 CDF.
        f << "\n# full unique-word histogram (words,pages)\n";
        for (uint32_t w = 0; w <= kWordsPerPage; ++w) {
            uint64_t n = 0;
            for (size_t i = 0; i < results_.size(); ++i) n += results_[i].uniqueHist[w];
            f << w << "," << n << "\n";
        }

        f << "\n# N, hpt_access_ratio, hwt_access_ratio\n";
        for (size_t b = 0; b < cfg_.trackerBudgets.size(); ++b) {
            double hp = 0.0, hw = 0.0;
            for (size_t i = 0; i < results_.size(); ++i) {
                hp += results_[i].hptAccessRatio[b];
                hw += results_[i].hwtAccessRatio[b];
            }
            f << cfg_.trackerBudgets[b] << "," << std::fixed << std::setprecision(4)
              << (hp / results_.size()) << "," << (hw / results_.size()) << "\n";
        }
    }

  private:
    struct Slot {
        uint32_t n = 0;
        SpaceSaving hpt, hwt;
        CountMinTopK hptCM, hwtCM;
    };

    ProbeConfig cfg_;
    CounterTable counters_;
    std::vector<Slot> slots_;
    uint32_t epoch_ = 0;
    uint64_t sinceEpoch_ = 0;
    std::vector<EpochResult> results_;
};

}  // namespace hotskew

#endif  // HOTSKEW_PROBE_HPP
