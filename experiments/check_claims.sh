#!/usr/bin/env bash
# check_claims.sh -- verify the numbers in docs/claims.md against the result files.
#
# Documents drift. This work revised its headline accuracy claim, the Count-Min
# result, and the measurement-window story, and each revision left stale copies
# elsewhere. This script re-derives the checkable numbers from results/ so that
# drift is caught rather than discovered by a reader.
#
# It checks values that come from committed result files. Claims derived from
# microbenchmarks that must be re-run (the kernel blind spot, the tracker self-test)
# are listed but not recomputed here; run them directly.
#
#   ./check_claims.sh

set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
cd "$REPO"

PY="./.venv/bin/python"
[[ -x "$PY" ]] || PY=python3
FAIL=0

ok()   { printf '  \033[32mOK  \033[0m %-46s %s\n' "$1" "$2"; }
bad()  { printf '  \033[31mFAIL\033[0m %-46s %s\n' "$1" "$2"; FAIL=$((FAIL+1)); }
SKIPPED=0
skip() { SKIPPED=$((SKIPPED+1)); printf '  \033[33m--  \033[0m %-46s %s\n' "$1" "$2"; }

# close <label> <actual> <expected> <tol>
close() {
  [[ -z "${2:-}" || "$2" == "nan" ]] && { skip "$1" "no data"; return; }
  awk -v a="$2" -v e="$3" -v t="$4" -v l="$1" 'BEGIN{d=a-e; if(d<0)d=-d; exit (d<=t)?0:1}' \
    && ok "$1" "$2 (expect $3)" || bad "$1" "$2 (expect $3 +/- $4)"
}

echo "Verifying docs/claims.md against results/"
echo
echo "Reproduction — max error across all five N:"
$PY - <<'PY' > /tmp/.claims_repro 2>/dev/null
import sys, os; sys.path.insert(0,'src/analysis')
import hotskew as H
rows=[("pr","results/spr-20t-ul/gapbs-pr.summary.txt","gapbs-pr",0.014),
      ("tc","results/spr-20t-ul/gapbs-tc.summary.txt","gapbs-tc",0.030),
      ("cc","results/spr-20t-ul/gapbs-cc.summary.txt","gapbs-cc",0.082),
      ("redis","results/spr-1t/redis-ycsba.summary.txt","redis",0.085),
      ("bfs","results/spr-20t-ul/gapbs-bfs.summary.txt","gapbs-bfs",0.095),
      ("sssp","results/spr-20t-ul/gapbs-sssp.summary.txt","gapbs-sssp",0.433),
      ("bc","results/spr-20t-ul/gapbs-bc.summary.txt","gapbs-bc",0.493),
      ("lib","results/spr-20t/liblinear.summary.txt","liblinear",0.577)]
for lbl,p,k,exp in rows:
    if not os.path.exists(p): print(f"{lbl} nan {exp}"); continue
    o=H.figure4_from_summary(p); m=H.M5_FIGURE4[k]
    print(f"{lbl} {max(abs(o[n]-m[n]) for n in H.FIG4_N):.4f} {exp}")
PY
while read -r lbl act exp; do close "max err, $lbl" "$act" "$exp" 0.005; done < /tmp/.claims_repro

echo
echo "Trackers (Space-Saving, ASLR pinned):"
tk() {
  local f="results/trackers/gapbs-$1.spacesaving.summary.txt"
  [[ -f "$f" ]] || { echo ""; return; }
  sed -n '/^# N, hpt_access_ratio/,/^$/p' "$f" | grep -v '^#' | awk -F, -v n="$2" '$1==n{print $2}'
}
close "bfs N=128"                "$(tk bfs 128)"  0.757 0.01
close "bfs N=8192"               "$(tk bfs 8192)" 0.767 0.01
close "cc  N=128"                "$(tk cc 128)"   0.657 0.01

echo
echo "Latency model:"
LAT=$($PY src/analysis/latency_model.py --config spr-20t 2>/dev/null \
      | awk '/geomean speedup vs all-CXL/{for(i=1;i<=NF;i++) if($i=="count-only") print $(i+1)}' \
      | tr -d 'x')
close "geomean speedup, count-only" "${LAT:-}" 1.505 0.02

echo
echo "Granularity sweep:"
gr() { awk -F, -v b="$1" -v p="$2" -v w="$3" '$1==b&&$2==p&&$3==w{print $4}' \
       results/granularity.csv results/granularity_redis.csv 2>/dev/null | head -1; }
close "bc  4KB/64B touched frac"   "$(gr bc 4096 64)"          0.485 0.005
close "bc  2MB/64B touched frac"   "$(gr bc 2097152 64)"       0.237 0.005
close "pr  4KB/64B touched frac"   "$(gr pr 4096 64)"          0.987 0.005
close "redis 4KB/64B touched frac" "$(gr redis-ycsba 4096 64)" 0.140 0.005
close "redis 4KB/512B touched frac" "$(gr redis-ycsba 4096 512)" 0.351 0.005

echo
echo "Not recomputed here (re-run the named tool):"
skip "kernel blind spot 5 vs 24,838,154" "src/profiler/validate/kernel_blindspot.c"
skip "cold-tail law 256->0.002, 512->1.000" "make -C src/sim test"
skip "calibration strides 1/4/16/64"        "src/profiler/validate/run_validation.sh"

echo
if [[ $FAIL -eq 0 && $SKIPPED -eq 0 ]]; then
  echo -e "\033[32mclaims.md is consistent with results/\033[0m"
elif [[ $FAIL -eq 0 ]]; then
  # Reporting "consistent" while quietly skipping unverifiable rows is how the
  # latency claims went stale without anyone noticing.
  echo -e "\033[33mno claim DISAGREES, but $SKIPPED were not checked -- see the -- lines above\033[0m"
else
  echo -e "\033[31m$FAIL claim(s) disagree with results/ -- fix claims.md or re-run\033[0m"
fi
rm -f /tmp/.claims_repro
exit $FAIL
