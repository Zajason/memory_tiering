#!/usr/bin/env bash
# setup_redis.sh -- build Redis and a YCSB driver for the sparse-access case.
#
# Why Redis matters here more than any other benchmark
# ----------------------------------------------------
# It is the extreme point of M5's Figure 4: 86% of its 4 KB pages have at most 25% of
# their 64 B words accessed, against ~0% for PageRank. A reproduction that gets
# PageRank right proves the tool measures density correctly; getting Redis right
# proves it measures *sparsity* correctly. Both ends are needed before the
# methodology can be trusted in between.
#
# Redis was also the workload M5 ran with the tightest LLC partition -- CAT mask
# 0x4000, one way of fifteen, 4 MB (see configs/spr-1t.env).
#
#   ./setup_redis.sh
#
# Requires: a C toolchain (have it), and for the YCSB path a JRE. If no JRE is
# present the script installs a self-contained C driver instead, which implements
# YCSB workload C semantics (100% read, Zipfian keys) without the Java dependency.

set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/../experiments/env.sh"

REDIS_VER="7.2.5"
YCSB_VER="0.17.0"
mkdir -p "$BENCH_ROOT"

# ---------------------------------------------------------------- redis-server
if [[ ! -x "$REDIS_DIR/src/redis-server" ]]; then
  echo ">> downloading and building Redis $REDIS_VER"
  tmp="$BENCH_ROOT/redis-$REDIS_VER.tar.gz"
  curl -fL --retry 3 -o "$tmp" "https://download.redis.io/releases/redis-$REDIS_VER.tar.gz"
  tar -xzf "$tmp" -C "$BENCH_ROOT"
  mv "$BENCH_ROOT/redis-$REDIS_VER" "$REDIS_DIR"
  rm -f "$tmp"

  cp "$REPO/src/profiler/roi/hotskew_roi.h" "$REDIS_DIR/src/"
fi

# ROI markers driven by the client. Redis writes the whole dataset during the YCSB
# load phase, touching every word of every page it allocates; only the query phase
# shows the skewed access pattern. The client sends ECHO HOTSKEW_ROI_BEGIN / _END
# between phases and we make echoCommand call the markers when it sees them.
#
# echoCommand has moved between files across Redis versions, so find it rather than
# hardcoding a path and silently patching nothing.
echo ">> installing ROI markers"
ECHO_SRC="$(grep -rl 'void echoCommand' "$REDIS_DIR/src" --include='*.c' | head -1)"
[[ -n "$ECHO_SRC" ]] || die "could not find echoCommand in $REDIS_DIR/src"
echo "   echoCommand lives in $(basename "$ECHO_SRC")"

python3 - "$ECHO_SRC" <<'PY'
import re, sys
path = sys.argv[1]
src = open(path).read()
if 'hotskew_roi' in src:
    print("   already patched")
    sys.exit(0)

if '#include "hotskew_roi.h"' not in src:
    # Put the include after the first existing include so it lands after any
    # feature-test macros at the top of the file.
    src = re.sub(r'(#include [<"][^>"]+[>"]\n)', r'\1#include "hotskew_roi.h"\n', src, count=1)

m = re.search(r'void\s+echoCommand\s*\(\s*client\s*\*\s*c\s*\)\s*\{', src)
if not m:
    sys.exit("could not locate the echoCommand body")

hook = '''
    /* hotskew: region-of-interest markers driven by the benchmark client. */
    if (c->argc == 2 && sdslen(c->argv[1]->ptr) >= 15) {
        const char *_m = c->argv[1]->ptr;
        if (!strcmp(_m, "HOTSKEW_ROI_BEGIN")) hotskew_roi_begin();
        else if (!strcmp(_m, "HOTSKEW_ROI_END")) hotskew_roi_end();
    }
'''
src = src[:m.end()] + hook + src[m.end():]
open(path, 'w').write(src)
print("   echoCommand patched")
PY

if [[ ! -x "$REDIS_DIR/src/redis-server" ]] || [[ "$ECHO_SRC" -nt "$REDIS_DIR/src/redis-server" ]]; then
  echo ">> building (this takes a few minutes)"
  make -C "$REDIS_DIR" -j"$(nproc)" MALLOC=libc
fi
n=$(nm "$REDIS_DIR/src/redis-server" 2>/dev/null | grep -c hotskew_roi || true)
[[ "$n" -ge 2 ]] || die "redis-server has no ROI symbols -- the patch did not take effect"
echo "   ROI markers present in redis-server"
[[ -x "$REDIS_DIR/src/redis-server" ]] || die "redis build failed"
echo "   redis-server ready: $REDIS_DIR/src/redis-server"

# ------------------------------------------------------------------ the driver
#
# Redis is profiled as a *server*: redis-server runs under Pin, a separate client
# process drives it. The ROI is delimited by the client, which sends a marker
# command between the load and query phases -- see experiments/run_redis.sh.
#
if command -v java >/dev/null 2>&1; then
  if [[ ! -d "$YCSB_DIR" ]]; then
    echo ">> downloading YCSB $YCSB_VER (matches what M5 used)"
    tmp="$BENCH_ROOT/ycsb.tar.gz"
    curl -fL --retry 3 -o "$tmp" \
      "https://github.com/brianfrankcooper/YCSB/releases/download/$YCSB_VER/ycsb-redis-binding-$YCSB_VER.tar.gz"
    tar -xzf "$tmp" -C "$BENCH_ROOT"
    mv "$BENCH_ROOT/ycsb-redis-binding-$YCSB_VER" "$YCSB_DIR"
    rm -f "$tmp"
  fi
  echo "   YCSB ready: $YCSB_DIR"
else
  cat <<'EOF'

   No JRE found, so YCSB cannot run. Building the standalone C driver instead.

   This is not a silent substitution: the C driver implements YCSB workload C
   (100% read, Zipfian key popularity, theta=0.99) directly over the Redis
   protocol. That is the access *distribution* that produces Figure 4's sparsity,
   which is what we are measuring. It is not a throughput-comparable YCSB run and
   should not be reported as one.

   To use real YCSB instead:  sudo apt install default-jre  &&  rerun this script.

EOF
  mkdir -p "$YCSB_DIR"
  cc -O2 -o "$YCSB_DIR/zipf_client" "$HERE/zipf_client.c" -lm
  echo "   built $YCSB_DIR/zipf_client"
fi

echo
echo "run with:  ./experiments/run_redis.sh"
