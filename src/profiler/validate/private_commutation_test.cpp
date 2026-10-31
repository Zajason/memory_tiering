#include "../pintool/cache_hierarchy.hpp"
#include "../pintool/paired_observer.hpp"
#include <array>
#include <cassert>
#include <sstream>
#include <tuple>
#include <vector>

using namespace hotskew;
struct Reference { unsigned thread; uint64_t line; AccessType type; };
struct Private { CacheLevel l1, l2; };

int main() {
    std::vector<Reference> trace;
    uint64_t random = 7;
    for (unsigned i = 0; i < 20000; ++i) {
        random = random * 6364136223846793005ULL + 1;
        trace.push_back({unsigned((random >> 32) % 4), (random >> 40) % 1024,
                         i % 3 ? ACCESS_READ : ACCESS_WRITE});
    }
    std::string expected;
    std::vector<std::tuple<unsigned,uint64_t,bool>> expectedEvents;
    for (bool computeAhead : {false,true}) {
        std::array<Private,4> caches;
        for (auto& c : caches) {
            assert(c.l1.init("l1",256,2,64));
            assert(c.l2.init("l2",1024,4,64));
        }
        CacheLevel llc; assert(llc.init("llc",4096,4,64));
        std::vector<PrivateResult> outcomes(trace.size());
        if (computeAhead) {
            // Deliberately compute entire per-thread sequences out of global order.
            for (unsigned thread=0; thread<4; ++thread)
                for (size_t i=0; i<trace.size(); ++i)
                    if (trace[i].thread==thread)
                        outcomes[i]=accessPrivate(caches[thread].l1,caches[thread].l2,
                                                  trace[i].line,trace[i].type);
        }
        PairedObserver paired;
        std::ostringstream csv;
        std::vector<std::tuple<unsigned,uint64_t,bool>> events;
        unsigned epoch=0, count=0;
        for (size_t i=0; i<trace.size(); ++i) {
            const auto& ref=trace[i];
            auto outcome=computeAhead ? outcomes[i] :
                accessPrivate(caches[ref.thread].l1,caches[ref.thread].l2,ref.line,ref.type);
            paired.record(ref.line,PairedObserver::ACCESSES);
            accessShared(llc,ref.line,outcome,[&](uint64_t line,bool write) {
                events.emplace_back(unsigned(i),line,write);
                if (!write) paired.record(line,PairedObserver::FILLS);
                paired.record(line,PairedObserver::TRAFFIC);
                ++count;
            });
            if (count>=97) { paired.endEpoch(csv,epoch++);count=0; }
            // Include explicit ROI partial-window boundaries as well as events.
            if (i % 701 == 700) { paired.endEpoch(csv,epoch++);count=0; }
        }
        paired.endEpoch(csv,epoch++);paired.finish(csv,epoch);
        if (!computeAhead) { expected=csv.str();expectedEvents=events; }
        else { assert(expected==csv.str());assert(expectedEvents==events); }
    }
}
