#!/usr/bin/env bash
# run_validation.sh -- assert that hotskew reports analytically known ground truth.
#
# Every case here has a word-density we can compute on paper. If any of them drifts,
# the tool is lying and no downstream figure can be trusted. Run this after any
# change to hotskew.cpp, cache_model.hpp or counter_table.hpp.
#
#   ./run_validation.sh [PIN_ROOT]

set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
PIN_ROOT="${1:-${PIN_ROOT:-$HOME/pin}}"
PIN="$PIN_ROOT/pin"
TOOL="$REPO/src/profiler/pintool/obj-intel64/hotskew.so"
SYNTH="$HERE/synth"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

[[ -x "$PIN"   ]] || { echo "no pin at $PIN (pass PIN_ROOT)"; exit 1; }
[[ -f "$TOOL"  ]] || { echo "build the tool first: make -C src/profiler/pintool PIN_ROOT=$PIN_ROOT"; exit 1; }
[[ -x "$SYNTH" ]] || { echo "building synth"; gcc -O1 -g -o "$SYNTH" "$HERE/synth.c" -lm || exit 1; }

# A deliberately small hierarchy: we want the synthetic buffer to overflow the LLC so
# that accesses actually reach the "DRAM" stream. Real runs use the SPR geometry.
CFG="-l1_kb 32 -l1_assoc 8 -l2_kb 256 -l2_assoc 8 -l3_kb 2048 -l3_assoc 16"
MIB=64
FAILURES=0

# field <file> <key>  -> value of "key   value" line
field() { grep -E "^$2 " "$1" | awk '{print $2}'; }

# check <label> <expected> <actual> <tolerance>
check() {
  local label="$1" exp="$2" got="$3" tol="$4"
  local ok
  ok=$(awk -v e="$exp" -v g="$got" -v t="$tol" 'BEGIN{d=e-g; if(d<0)d=-d; print (d<=t)?"1":"0"}')
  if [[ "$ok" == "1" ]]; then
    printf '  \033[32mPASS\033[0m  %-34s expected %-8s got %s\n' "$label" "$exp" "$got"
  else
    printf '  \033[31mFAIL\033[0m  %-34s expected %-8s got %s (tol %s)\n' "$label" "$exp" "$got" "$tol"
    FAILURES=$((FAILURES+1))
  fi
}

run() { # run <name> <synth args...>
  local name="$1"; shift
  "$PIN" -t "$TOOL" $CFG -epoch 0 -dump_pages 0 -roi_rtn synth_roi \
         -tag "$name" -o "$OUT/$name" -- "$SYNTH" "$@" >/dev/null 2>&1
}

echo "hotskew validation  (pin=$PIN_ROOT)"
echo
echo "1. Strided access -- a page must show exactly 4096/stride unique words"
for stride in 4096 1024 256 64; do
  run "s$stride" stride "$MIB" "$stride" 4
  check "stride=$stride" "$((4096/stride))" "$(field "$OUT/s$stride.summary.txt" mean_unique_words)" 0.05
done

echo
echo "2. Dense scan -- every word of every page"
run dense dense "$MIB" 0 4
check "dense mean_unique_words" 64 "$(field "$OUT/dense.summary.txt" mean_unique_words)" 0.1

echo
echo "3. Mixture -- p% of pages dense, the rest one word"
for pct in 10 25 50; do
  run "hs$pct" hotset "$MIB" "$pct" 4
  exp=$(awk -v p="$pct" 'BEGIN{printf "%.3f", (100-p)/100*1 + p/100*64}')
  check "hotset ${pct}% mean_unique" "$exp" "$(field "$OUT/hs$pct.summary.txt" mean_unique_words)" 0.15
  # P(<=4 words) must equal the sparse fraction.
  ple4=$(awk '/^  4 / {print $3}' "$OUT/hs$pct.summary.txt")
  exp4=$(awk -v p="$pct" 'BEGIN{printf "%.3f", (100-p)/100}')
  check "hotset ${pct}% P(<=4 words)" "$exp4" "$ple4" 0.02
done

echo
echo "4. Cache filter must actually filter"
run nofilt stride "$MIB" 64 4
nof=$(field "$OUT/nofilt.summary.txt" llc_miss_ratio)
# A streaming scan of 64 MiB through a 2 MiB LLC should miss essentially always.
check "streaming LLC miss ratio" 1.0 "$nof" 0.02
"$PIN" -t "$TOOL" -cache 0 -epoch 0 -dump_pages 0 -roi_rtn synth_roi \
       -o "$OUT/raw" -- "$SYNTH" stride "$MIB" 4096 4 >/dev/null 2>&1
check "cache=0 counts every ref" \
      "$(field "$OUT/raw.summary.txt" mem_refs_profiled)" \
      "$(field "$OUT/raw.summary.txt" dram_accesses)" 0

echo
if [[ $FAILURES -eq 0 ]]; then
  echo -e "\033[32mall checks passed\033[0m"
else
  echo -e "\033[31m$FAILURES check(s) failed\033[0m"
fi
exit $FAILURES
