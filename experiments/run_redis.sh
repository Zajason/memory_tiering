#!/usr/bin/env bash
# run_redis.sh -- profile redis-server under a Zipfian key-value workload.
#
# Redis is the extreme sparse point of M5's Figure 4: 86% of pages have at most 25%
# of their 64 B words touched. It is also structurally different from the other
# benchmarks here -- a server driven by a separate client, not a batch job -- so it
# gets its own runner.
#
#   ./run_redis.sh [config] [records] [ops]
#
# Defaults: config spr-1t (M5 gave Redis a 1-way, 4 MB CAT partition), 4M records of
# 1 KB (~4 GB of values), 20M Zipfian GETs.
#
# The server runs under Pin; the client runs natively alongside it. The client sends
# ECHO HOTSKEW_ROI_BEGIN / _END between the load and query phases, and the patched
# echoCommand calls the ROI markers, so only the query phase is measured.

set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"
check_prereqs

CONFIG="${1:-spr-1t}"
RECORDS="${2:-4000000}"
OPS="${3:-20000000}"
PORT="${REDIS_PORT:-16379}"

CFG_FILE="$REPO/configs/$CONFIG.env"
[[ -f "$CFG_FILE" ]] || die "no such config: $CFG_FILE"
CACHE_OFF=0
# shellcheck disable=SC1090
source "$CFG_FILE"

SERVER="$REDIS_DIR/src/redis-server"
[[ -x "$SERVER" ]] || die "no redis-server -- run benchmarks/setup_redis.sh"

CLIENT="$YCSB_DIR/zipf_client"
USE_YCSB=0
if [[ -x "$YCSB_DIR/bin/ycsb.sh" ]] && command -v java >/dev/null 2>&1; then
  USE_YCSB=1
elif [[ ! -x "$CLIENT" ]]; then
  die "no client -- run benchmarks/setup_redis.sh"
fi

OUTDIR="$RESULTS_ROOT/$CONFIG"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/redis"

if [[ "$CACHE_OFF" == "1" ]]; then
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

echo "=== redis [$CONFIG]  records=$RECORDS ops=$OPS epoch=${EPOCH_M}M ==="

# save '' disables RDB snapshotting: a background save would fork the server and
# double-count its memory traffic. appendonly no for the same reason.
"$PIN" -t "$TOOL" "${CACHE_ARGS[@]}" -epoch "$EPOCH_M" -dump_pages "$DUMP_PAGES" \
       -tag redis -o "$OUT" \
       -roi_begin hotskew_roi_begin -roi_end hotskew_roi_end \
       -- "$SERVER" --port "$PORT" --save '' --appendonly no --protected-mode no \
       > "$OUT.server.log" 2>&1 &
SERVER_PID=$!

echo "   waiting for the server to accept connections"
for _ in $(seq 1 120); do
  if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then exec 3<&- 3>&-; break; fi
  sleep 1
done
(exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null || {
  echo "server never came up; log:" >&2; tail -20 "$OUT.server.log" >&2; exit 1; }

if [[ "$USE_YCSB" == "1" ]]; then
  echo "   driving with YCSB workloadc"
  ( cd "$YCSB_DIR" && \
    ./bin/ycsb.sh load redis -s -P workloads/workloadc \
      -p redis.host=127.0.0.1 -p redis.port="$PORT" -p recordcount="$RECORDS" \
      -threads 8 && \
    ./bin/ycsb.sh run redis -s -P workloads/workloadc \
      -p redis.host=127.0.0.1 -p redis.port="$PORT" -p recordcount="$RECORDS" \
      -p operationcount="$OPS" -threads 8 ) > "$OUT.client.log" 2>&1
  echo "   NOTE: with real YCSB the ROI markers are not sent, so the whole server"
  echo "         lifetime is measured. Use the zipf_client path for ROI-bounded runs."
else
  echo "   driving with the standalone Zipfian client"
  "$CLIENT" 127.0.0.1 "$PORT" "$RECORDS" "$OPS" 0.99 2>&1 | tee "$OUT.client.log"
fi

echo "   shutting the server down so the tool writes its summary"
kill -TERM "$SERVER_PID" 2>/dev/null
wait "$SERVER_PID" 2>/dev/null
SERVER_PID=""

echo
if grep -q "^page_observations" "$OUT.summary.txt" 2>/dev/null; then
  sed -n '/^# M5 Figure 4/,/^# P(page has at least/p' "$OUT.summary.txt"
  grep -E "^(mean_unique_words|top4_word_share|llc_miss_ratio|epochs|page_observations)" "$OUT.summary.txt"
  echo
  echo "M5 Figure 4 for redis:  P(<=4)=0.51  P(<=8)=0.765  P(<=16)=0.865  P(<=32)=0.925  P(<=48)=0.94"
else
  echo "no usable summary -- see $OUT.summary.txt and $OUT.server.log" >&2
  exit 1
fi
