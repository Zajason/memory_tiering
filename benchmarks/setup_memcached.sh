#!/usr/bin/env bash
# setup_memcached.sh -- fetch, patch and build memcached with ROI markers.
#
# Why memcached is worth adding
# -----------------------------
# It is one of M5's fourteen Figure 4 bars, it needs no licence, and the paper
# states its value in prose rather than only in the bar chart:
#
#     "the likelihood of a page having 25% or fewer of its unique words accessed
#      is 86%, 76%, and 74% for Redis, Memcached, and CacheLib"
#
# So the target is P(<=16) = 0.76 exactly, with no digitising error.
#
# What differs from Redis, and why it matters
# -------------------------------------------
# memcached has no hash type. A YCSB record can only be one flat value, where the
# Redis runs deliberately use 10 x 100 B hash fields. That is not cosmetic: the
# record layout decides which values share a 4 KB page and therefore how many of
# that page's 64 B words a skewed read stream touches -- it moves the number
# Figure 4 reports. Treat the memcached result as a flat-layout measurement.
#
# The ROI markers
# ---------------
# Same trick as Redis. The client sends a marker between the load and query
# phases and the server calls hotskew_roi_begin()/end() when it sees it, so the
# measurement covers the query phase only and not the multi-gigabyte load. Redis
# hooks echoCommand; memcached has no ECHO, so we add two no-arg commands beside
# the existing "version" handler.
#
# Requires libevent-dev (memcached will not configure without it).
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
source "$REPO/experiments/env.sh" 2>/dev/null || true
: "${BENCH_ROOT:=$REPO/workloads}"
MC_VER="${MC_VER:-1.6.21}"
MC_DIR="$BENCH_ROOT/memcached-$MC_VER"

die() { echo "ERROR: $*" >&2; exit 1; }

[[ -f /usr/include/event2/event.h ]] || die \
  "libevent-dev is missing. Install it first:
     sudo apt-get install -y libevent-dev"

mkdir -p "$BENCH_ROOT"
if [[ ! -d "$MC_DIR" ]]; then
  echo ">> fetching memcached $MC_VER"
  tmp="$BENCH_ROOT/memcached-$MC_VER.tar.gz"
  curl -fL --retry 3 -o "$tmp" "https://memcached.org/files/memcached-$MC_VER.tar.gz"
  tar -xzf "$tmp" -C "$BENCH_ROOT"
  rm -f "$tmp"
fi

# The ROI header lives with the profiler; copy it in so the build finds it.
cp "$REPO/src/profiler/validate/hotskew_roi.h" "$MC_DIR/hotskew_roi.h" 2>/dev/null \
  || cp "$(find "$REPO/src" -name hotskew_roi.h | head -1)" "$MC_DIR/hotskew_roi.h"

echo ">> installing ROI markers"
# Anchor on the existing "version" command rather than a line number: the file is
# restructured between memcached releases, and a hardcoded offset would patch
# nothing while still exiting 0.
PROTO_SRC="$(grep -rl '"version"' "$MC_DIR" --include='proto_text.c' | head -1)"
[[ -n "$PROTO_SRC" ]] || die "could not find the version-command handler in proto_text.c"

python3 - "$PROTO_SRC" <<'PYEOF'
import re, sys
path = sys.argv[1]
src = open(path).read()
if 'hotskew_roi' in src:
    print("   already patched")
    sys.exit(0)

if '#include "hotskew_roi.h"' not in src:
    src = re.sub(r'(#include [<"][^>"]+[>"]\n)', r'\1#include "hotskew_roi.h"\n',
                 src, count=1)

# Insert the two branches immediately BEFORE the "version" dispatch's `if`
# keyword, not before the whole clause. The dispatch reads
# `} else if (strcmp(... "version") ...)`, so inserting ahead of the clause
# produced `} else    } else if (...)` and failed to compile. Splitting at the
# `if` leaves whatever `} else ` precedes it intact.
m = re.search(r'if\s*\(\s*strcmp\s*\(\s*tokens\s*\[\s*COMMAND_TOKEN\s*\]'
              r'\s*\.\s*value\s*,\s*"version"\s*\)\s*==\s*0\s*\)', src)
if not m:
    sys.exit('could not locate the "version" dispatch; memcached layout changed')

hook = ('if (strcmp(tokens[COMMAND_TOKEN].value, "hotskew_roi_begin") == 0) {\n'
        '        hotskew_roi_begin();\n'
        '        out_string(c, "OK");\n'
        '    } else if (strcmp(tokens[COMMAND_TOKEN].value, "hotskew_roi_end") == 0) {\n'
        '        hotskew_roi_end();\n'
        '        out_string(c, "OK");\n'
        '    } else ')
src = src[:m.start()] + hook + src[m.start():]
open(path, 'w').write(src)
print("   proto_text.c patched")
PYEOF

if [[ ! -x "$MC_DIR/memcached" ]] || [[ "$PROTO_SRC" -nt "$MC_DIR/memcached" ]]; then
  echo ">> building"
  ( cd "$MC_DIR"
    [[ -f Makefile ]] || ./configure --disable-extstore CPPFLAGS="-I$MC_DIR"
    make -j"$(nproc)" CPPFLAGS="-I$MC_DIR" )
fi

n=$(nm "$MC_DIR/memcached" 2>/dev/null | grep -c hotskew_roi || true)
[[ "$n" -ge 2 ]] || die "memcached has no ROI symbols -- the patch did not take effect"
echo "   ROI markers present in memcached"
echo "ready: $MC_DIR/memcached"
