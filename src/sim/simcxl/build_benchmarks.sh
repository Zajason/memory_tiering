#!/usr/bin/env bash
# Build the benchmarks for full-system gem5: static, with m5 ROI markers.
#
# Static because the guest is Ubuntu 18.04 and this host is 26.04 -- a
# dynamically linked binary built here will not run there.
#
# The ROI markers reuse benchmarks/patches/gapbs-roi.patch unchanged. Only the
# hotskew_roi.h implementation is swapped (empty symbols -> m5_exit), so the
# simulator measures exactly the region Pin measured.
set -euo pipefail
REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
SIM="${SIMCXL_DIR:-$REPO/../simcxl}"
M5A="$SIM/util/m5/build/x86/out/libm5.a"
[[ -f "$M5A" ]] || { echo "build m5ops first: (cd $SIM/util/m5 && scons build/x86/out/libm5.a)"; exit 1; }

rm -rf "$REPO/bench/gapbs-gem5"; mkdir -p "$REPO/bench/gapbs-gem5"
cp -r "$REPO/bench/gapbs/src" "$REPO/bench/gapbs/Makefile" "$REPO/bench/gapbs-gem5/"
cp "$REPO/src/sim/simcxl/hotskew_roi_m5.h" "$REPO/bench/gapbs-gem5/src/hotskew_roi.h"
cd "$REPO/bench/gapbs-gem5"
# The GAPBS rule puts $(CXX_FLAGS) before $<, so a static archive added there
# would be scanned before the objects that need it. Compile directly instead.
for k in sssp bc; do
  g++ -std=c++11 -O3 -Wall -static -I"$SIM/include" "src/$k.cc" -o "$k" "$M5A"
done
echo "built: $(ls -1 sssp bc | tr '\n' ' ')"
