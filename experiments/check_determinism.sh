#!/usr/bin/env bash
# check_determinism.sh -- run the same measurement twice and diff it.
#
# Why this exists
# ---------------
# ASLR made tracker runs non-deterministic, and with one sample per configuration
# that variance was read as an algorithmic property of Count-Min Sketch (report §6.1).
# Two identical invocations gave access-count ratios of 0.1726 and 0.1803.
#
# Layout is pinned with setarch -R now. This script demonstrates that rather than
# asserting it, and covers both classes of metric:
#
#   Figure 4      expected identical with or WITHOUT pinning, because the metric
#                 depends on within-page word offsets, which are translation-
#                 invariant (methodology §2).
#   tracker       expected identical only WITH pinning, because trackers key on page
#                 numbers and Count-Min hashes them.
#
# The second check is the one that can fail, and it is deliberately run both ways so
# that a regression in the pinning shows up as a difference rather than as silence.

set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"
check_prereqs

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
GRAPH="$GRAPH_DIR/kron-${GRAPH_SCALE}.sg"
[[ -f "$GRAPH" ]] || die "missing $GRAPH -- run benchmarks/setup_gapbs.sh"
FAIL=0

# run <out> <pin:0|1>
run() {
  local pre=(); [[ "$2" == 1 ]] && pre=(setarch "$(uname -m)" -R)
  ( cd "$GAPBS_DIR" && OMP_NUM_THREADS=1 "${pre[@]}" \
      "$PIN" -t "$TOOL" -cache 1 -l1_kb 48 -l1_assoc 12 -l2_kb 2048 -l2_assoc 16 \
             -l3_kb 36864 -l3_assoc 9 -epoch 10 -dump_pages 0 \
             -track 1 -track_algo cmsketch -track_n 512 -track_k 128 \
             -roi_begin hotskew_roi_begin -roi_end hotskew_roi_end \
             -o "$1" -- ./bfs -f "$GRAPH" -n 1 ) >/dev/null 2>&1
}
fig4()  { awk '/^ 16 /{print $3}' "$1.summary.txt"; }
words() { awk '/^mean_unique_words/{print $2}' "$1.summary.txt"; }
cm()    { sed -n '/^# N, hpt/,/^$/p' "$1.summary.txt" | grep -v '^#' | cut -d, -f2; }

cmp3() { # cmp3 <label> <a> <b> <must_match:yes|no>
  if [[ "$2" == "$3" ]]; then
    [[ "$4" == yes ]] && printf '  \033[32mOK  \033[0m %-38s %s == %s\n' "$1" "$2" "$3" \
                      || printf '  \033[33m--  \033[0m %-38s %s == %s (matched anyway)\n' "$1" "$2" "$3"
  else
    if [[ "$4" == yes ]]; then
      printf '  \033[31mFAIL\033[0m %-38s %s != %s\n' "$1" "$2" "$3"; FAIL=$((FAIL+1))
    else
      printf '  \033[32mOK  \033[0m %-38s %s != %s (variance expected)\n' "$1" "$2" "$3"
    fi
  fi
}

echo "Determinism check -- BFS on kron-${GRAPH_SCALE}, two identical runs each way"
echo
echo "With ASLR pinned (setarch -R) -- everything must be identical:"
run "$TMP/p1" 1; run "$TMP/p2" 1
cmp3 "Figure 4  P(<=16)"      "$(fig4  "$TMP/p1")" "$(fig4  "$TMP/p2")" yes
cmp3 "mean unique words"      "$(words "$TMP/p1")" "$(words "$TMP/p2")" yes
cmp3 "Count-Min access ratio" "$(cm    "$TMP/p1")" "$(cm    "$TMP/p2")" yes

echo
echo "Without pinning -- Figure 4 must still be identical; the tracker need not be:"
run "$TMP/u1" 0; run "$TMP/u2" 0
cmp3 "Figure 4  P(<=16)"      "$(fig4  "$TMP/u1")" "$(fig4  "$TMP/u2")" yes
cmp3 "mean unique words"      "$(words "$TMP/u1")" "$(words "$TMP/u2")" yes
cmp3 "Count-Min access ratio" "$(cm    "$TMP/u1")" "$(cm    "$TMP/u2")" no

echo
if [[ $FAIL -eq 0 ]]; then
  echo -e "\033[32mDeterminism as documented: Figure 4 is layout-invariant, trackers need pinning.\033[0m"
else
  echo -e "\033[31m$FAIL check(s) failed -- a result that should be reproducible is not.\033[0m"
fi
exit $FAIL
