#!/usr/bin/env bash
# setup_cachelib.sh -- fetch, patch and build CacheLib with ROI markers.
#
# Read this before running it. CacheLib is the most expensive of M5's fourteen
# bars by a wide margin and the least informative, and it is worth knowing that
# up front rather than three hours in.
#
# What it costs
# -------------
#   * contrib/build.sh compiles folly, fizz, wangle and fbthrift FROM SOURCE.
#     That is roughly 1-3 hours on this machine and tens of GB of build tree.
#   * Those projects track a moving HEAD. A CacheLib release pinned to a folly
#     commit from its own era frequently fails to build against a newer
#     toolchain -- and this box has gcc 15, which is far newer than anything
#     CacheLib has been tested against.
#   * Ten system packages are required before any of that starts.
#
# What it buys
# ------------
#   One bar. The paper states its value in prose -- "the likelihood of a page
#   having 25% or fewer of its unique words accessed is 86%, 76%, and 74% for
#   Redis, Memcached, and CacheLib" -- so the target is P(<=16) = 0.74 exactly.
#
# The honest recommendation: do memcached first (done, 0.006 against its stated
# value), and treat CacheLib as optional. If the build fights back, the right
# move is to stop and say "not attempted, build cost" rather than spend a day on
# a single bar.
#
# Workload shape
# --------------
# CacheLib is a library, not a server. Its benchmark driver is `cachebench`,
# driven by a JSON config rather than a network client, so the zipf_client.c
# path is not used at all. The closest analogue to our Redis/memcached runs is
# cachebench's own hit_ratio/graph_cache_leader workload with a Zipfian
# popularity distribution, which is what the config below asks for.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
source "$REPO/experiments/env.sh" 2>/dev/null || true
: "${BENCH_ROOT:=$REPO/workloads}"
CL_DIR="$BENCH_ROOT/CacheLib"

die() { echo "ERROR: $*" >&2; exit 1; }

MISSING=()
for p in libgflags-dev libgoogle-glog-dev libfmt-dev libboost-all-dev \
         libdouble-conversion-dev libsnappy-dev liblz4-dev libzstd-dev \
         libsodium-dev libaio-dev libjemalloc-dev libssl-dev cmake; do
  dpkg -s "$p" >/dev/null 2>&1 || MISSING+=("$p")
done
if ((${#MISSING[@]})); then
  die "missing system packages. Install them first:

     sudo apt-get install -y ${MISSING[*]}"
fi

mkdir -p "$BENCH_ROOT"
if [[ ! -d "$CL_DIR" ]]; then
  echo ">> cloning CacheLib (shallow)"
  git clone --depth 1 https://github.com/facebook/CacheLib.git "$CL_DIR"
fi

cp "$(find "$REPO/src" -name hotskew_roi.h | head -1)" "$CL_DIR/hotskew_roi.h"

echo ">> installing ROI markers in cachebench"
# cachebench runs a setup phase (populating the cache) and then the measured
# phase, exactly like our Redis and memcached runs. Bracket only the second.
# Anchored on the runner's entry point rather than a line number, and it fails
# loudly if the anchor is gone.
CB_SRC="$(grep -rl 'class Runner' "$CL_DIR/cachelib/cachebench" --include='*.cpp' 2>/dev/null | head -1)"
[[ -n "$CB_SRC" ]] || die "could not find the cachebench Runner; CacheLib layout changed"

python3 - "$CB_SRC" <<'PYEOF'
import re, sys
path = sys.argv[1]
src = open(path).read()
if 'hotskew_roi' in src:
    print("   already patched")
    sys.exit(0)
if '#include "hotskew_roi.h"' not in src:
    src = re.sub(r'(#include [<"][^>"]+[>"]\n)', r'\1#include "hotskew_roi.h"\n',
                 src, count=1)
# Runner::run is where the measured phase begins, after the cache is populated.
m = re.search(r'(bool|void)\s+Runner::run\s*\([^)]*\)\s*\{', src)
if not m:
    sys.exit("could not locate Runner::run")
src = src[:m.end()] + "\n  hotskew_roi_begin();\n" + src[m.end():]
open(path, 'w').write(src)
print("   cachebench patched (ROI opens at Runner::run)")
PYEOF

echo ">> building -- this compiles folly/fizz/wangle/fbthrift and takes 1-3 hours"
( cd "$CL_DIR" && ./contrib/build.sh -j "$(nproc)" -T ) \
  || die "CacheLib build failed.

This is the expected failure mode, not a surprise: CacheLib pins folly to a
commit from its own release era and this machine has gcc 15. Options, in order
of sanity:
  1. Record CacheLib as 'not attempted, build cost' and move on. It is one bar.
  2. Build inside a container with an older toolchain (gcc 12, Ubuntu 22.04).
  3. Try an older CacheLib release tag that matches an older folly."

echo "ready: $CL_DIR/opt/cachelib/bin/cachebench"
