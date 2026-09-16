#!/usr/bin/env bash
# run_trackers.sh -- Deliverable 1: score M5's HPT and HWT against exact counts.
#
#   ./run_trackers.sh [benchmarks...]      (default: bfs cc tc pr)
#
# This is M5's Figure 8, reproduced without their FPGA.
#
# PAC and WAC give an exact count for every page and word. That is not buildable in a
# controller -- 256 GB at 4 KB granularity is 64M counters. M5's answer is a bounded
# top-K tracker with a fixed entry budget. The question their Figure 8 asks is: how
# close does the bounded approximation get to the exact answer, per unit of hardware?
#
# Because the trackers run inside the pintool alongside the exact counters, every run
# scores the approximation against ground truth in the same epoch, on the same stream.
# All budgets are fed that one stream in a single pass, so the whole accuracy-vs-cost
# curve costs one execution per benchmark rather than one per point.
#
# Budgets: M5's artifact names "Space-saving 50 counter" and "Count-Min Sketch 2K
# counter" as their two configured designs, so the sweep brackets both.

set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"
check_prereqs

BUDGETS="${TRACK_BUDGETS:-50,128,512,2048,8192}"
K="${TRACK_K:-128}"
OUTDIR="$RESULTS_ROOT/trackers"
mkdir -p "$OUTDIR"

BENCHES=("${@:-bfs cc tc pr}")
read -r -a BENCHES <<< "${BENCHES[*]}"

export OMP_NUM_THREADS=1

for algo in spacesaving cmsketch; do
  for k in "${BENCHES[@]}"; do
    case "$k" in
      sssp) graph="$GRAPH_DIR/kron-${GRAPH_SCALE}.wsg" ;;
      tc)   graph="$GRAPH_DIR/kron-21.sg" ;;   # tc is superlinear in edges
      *)    graph="$GRAPH_DIR/kron-${GRAPH_SCALE}.sg" ;;
    esac
    [[ -f "$graph" ]] || { echo "skip $k: no $graph"; continue; }
    out="$OUTDIR/gapbs-$k.$algo"
    echo "=== $k [$algo]  N in {$BUDGETS}  K=$K ==="
    ( cd "$BENCH_ROOT/gapbs" && \
      "${SETARCH[@]}" "$PIN" -t "$TOOL" -cache 1 -l1_kb 48 -l1_assoc 12 -l2_kb 2048 -l2_assoc 16 \
             -l3_kb 36864 -l3_assoc 9 -epoch "${EPOCH_M}" -dump_pages 0 \
             -track 1 -track_algo "$algo" -track_n "$BUDGETS" -track_k "$K" \
             -roi_begin hotskew_roi_begin -roi_end hotskew_roi_end \
             -tag "gapbs-$k" -o "$out" -- "./$k" -f "$graph" -n 1 \
    ) > "$out.run.log" 2>&1
    if grep -q "^# M5 Figure 8" "$out.summary.txt" 2>/dev/null; then
      sed -n '/^# M5 Figure 8/,/^$/p' "$out.summary.txt" | grep -v '^#'
    else
      echo "  no tracker output -- see $out.run.log" >&2
    fi
    echo
  done
done
echo TRACKERS_DONE
