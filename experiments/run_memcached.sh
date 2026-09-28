#!/usr/bin/env bash
# run_memcached.sh -- profile memcached under the hotskew pintool.
#
#   ./run_memcached.sh [config] [records] [ops]
#
# Structurally identical to run_redis.sh: the pintool attaches to the server, the
# client drives a YCSB-style load then a Zipfian query phase, and ROI markers sent
# between the two phases keep the multi-gigabyte load out of the measurement.
#
# Target from the paper's prose: P(<=16) = 0.76. That is an exact figure, not a
# digitised bar, so this run has an unusually sharp pass/fail.
#
# The record is one flat 1000 B value, because memcached has no hash type. The
# Redis runs use 10 x 100 B fields, and the layout moves the result, so the two
# are not directly comparable -- see benchmarks/setup_memcached.sh.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"
check_prereqs

CONFIG="${1:-spr-1t}"
RECORDS="${2:-2000000}"
OPS="${3:-10000000}"
PORT="${MC_PORT:-21311}"
MC_VER="${MC_VER:-1.6.21}"
SERVER="$BENCH_ROOT/memcached-$MC_VER/memcached"
CLIENT="$REPO/benchmarks/zipf_client"

[[ -x "$SERVER" ]] || die "memcached not built -- run benchmarks/setup_memcached.sh"
[[ -x "$CLIENT" ]] || gcc -O2 -Wall -o "$CLIENT" "$REPO/benchmarks/zipf_client.c" -lm

load_config "$CONFIG"
OUTDIR="$REPO/results/$CONFIG"; mkdir -p "$OUTDIR"
OUT="$OUTDIR/memcached"

if [[ "${NO_CACHE:-0}" == 1 ]]; then
  CACHE_ARGS=(-cache 0)
else
  CACHE_ARGS=(-cache 1 -l1_kb "$L1_KB" -l1_assoc "$L1_ASSOC"
              -l2_kb "$L2_KB" -l2_assoc "$L2_ASSOC"
              -l3_kb "$L3_KB" -l3_assoc "$L3_ASSOC")
fi

cleanup() {
  [[ -n "${SERVER_PID:-}" ]] && kill "$SERVER_PID" 2>/dev/null
  wait "${SERVER_PID:-}" 2>/dev/null
}
trap cleanup EXIT

echo "=== memcached [$CONFIG]  records=$RECORDS ops=$OPS epoch=${EPOCH_M}M ==="

# -m sets the slab budget in MB; it must exceed the dataset or memcached evicts and
# the query phase stops touching the pages the load created, which would look like
# sparsity that is really capacity eviction.
SLAB_MB="${MC_SLAB_MB:-$(( RECORDS / 1000 * 2 + 1024 ))}"
echo "   slab budget ${SLAB_MB} MB for $(( RECORDS / 1000 ))k records of 1000 B"

"$PIN" -t "$TOOL" "${CACHE_ARGS[@]}" -epoch "$EPOCH_M" -dump_pages "$DUMP_PAGES" \
       -tag "memcached" -o "$OUT" \
       -roi_begin hotskew_roi_begin -roi_end hotskew_roi_end \
       -- "$SERVER" -p "$PORT" -m "$SLAB_MB" -t 1 -u "$(id -un)" \
       > "$OUT.server.log" 2>&1 &
SERVER_PID=$!

echo "   waiting for the server to accept connections"
for _ in $(seq 1 120); do
  if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then exec 3<&- 3>&-; break; fi
  sleep 1
done
(exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null || {
  echo "server never came up; log:" >&2; tail -20 "$OUT.server.log" >&2; exit 1; }

PROTO=memcached "$CLIENT" 127.0.0.1 "$PORT" "$RECORDS" "$OPS" 0.99 0.5 \
  > "$OUT.client.log" 2>&1 || { tail -20 "$OUT.client.log" >&2; exit 1; }

echo "   client done; stopping the server so the pintool writes its summary"
kill "$SERVER_PID" 2>/dev/null; wait "$SERVER_PID" 2>/dev/null || true
SERVER_PID=

[[ -f "$OUT.summary.txt" ]] || die "no summary written -- check $OUT.server.log"
awk '/^mean_unique_words|^epochs|^dram_accesses/{print "   "$0}' "$OUT.summary.txt"
echo "   target from the paper: P(<=16) = 0.76"
