// Header-only checks for the window ladder and the prefetcher model.
//   g++ -std=c++17 -I. test_ladder_prefetch.cpp -o /tmp/t && /tmp/t
#include "paired_observer.hpp"
#include "prefetcher.hpp"
#include <sstream>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <set>
using namespace hotskew;
int main(){
  // ladder: 8 epochs -> level 3 has exactly one window and must equal "whole";
  // level 1 must equal a brute-force OR of epoch pairs.
  PairedObserver o; std::ostringstream out; srand(7);
  std::map<uint64_t,uint64_t> pair; uint64_t brute[65]={};
  for(int e=0;e<8;e++){
    for(int i=0;i<20000;i++){ uint64_t line=rand()%(64*900);
      o.record(line,PairedObserver::TRAFFIC); pair[line>>6]|=1ull<<(line&63);}
    if(e%2==1){ for(auto&kv:pair) brute[__builtin_popcountll(kv.second)]++; pair.clear(); }
    o.endEpoch(out,e);
  }
  uint64_t whole[3][3][65]={}; PairedObserver::histograms(o.whole,whole);
  assert(o.done[3]==1 && o.done[1]==4 && o.done[2]==2 && o.done[4]==0 && o.fill[4]==1);
  for(int n=0;n<=64;n++){ assert(o.ladder[3][2][0][n]==whole[2][0][n]); assert(o.ladder[1][2][0][n]==brute[n]); }
  // 5 epochs: tails exist at the right levels
  PairedObserver q; for(int e=0;e<5;e++){ q.record(e,PairedObserver::TRAFFIC); q.endEpoch(out,e);}
  assert(q.done[1]==2 && q.fill[1]==1 && q.done[2]==1 && q.fill[2]==0 && q.fill[3]==1);
  // prefetcher: ascending sweep of one page
  Prefetcher p; std::set<uint64_t> got; unsigned maxPer=0; uint64_t base=64*1000;
  for(uint64_t l=base;l<base+64;l++){ unsigned n=0;
    p.onL2Lookup(l,true,[&](uint64_t x){ ++n; assert((x>>6)==(base>>6)); if(x!=(l^1)) assert(x>l && x-l<=20); got.insert(x);});
    if(n>maxPer)maxPer=n; }
  assert(maxPer<=3);                       // spatial + two streamer
  // isolated single touches: only the pair line, never a stream
  Prefetcher r; unsigned extra=0;
  for(int i=0;i<1000;i++){ uint64_t l=(uint64_t)(rand()%5000)*64+ (rand()%64);
    r.onL2Lookup(l,true,[&](uint64_t x){ if(x!=(l^1)) ++extra; }); }
  // descending
  Prefetcher d; unsigned down=0;
  for(uint64_t l=base+63;l>base+40;l--) d.onL2Lookup(l,false,[&](uint64_t x){ assert(x<l && l-x<=20 && (x>>6)==(base>>6)); ++down;});
  printf("ok ladder; ascending prefetched=%zu maxPerLookup=%u randomExtra=%u descending=%u\n",got.size(),maxPer,extra,down);
}
