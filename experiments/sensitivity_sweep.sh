#!/usr/bin/env bash
# sensitivity_sweep.sh -- how much does each methodological choice move the answer?
#
# M5's Figure 4 is a single bar per benchmark. It is not obvious from the paper how
# much that bar depends on choices the paper does not state: how long the measurement
# window is, how big the dataset is, how many kernel invocations the window spans.
# This script measures exactly that, so the reproduction can report a curve with the
# paper's point marked on it rather than one number and a claim.
#
#   ./sensitivity_sweep.sh [axis]
#
#   axis: scale | trials | epoch | cache | threads | window | all   (default: all)
#
# Output: results/sensitivity/<axis>.csv

set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"
check_prereqs

AXIS="${1:-all}"
BENCH_KERNEL="${SWEEP_KERNEL:-bfs}"
OUTDIR="$RESULTS_ROOT/sensitivity"
mkdir -p "$OUTDIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# one_run <graph> <trials> <epoch_M> <l3_kb> <l3_assoc> <threads> <roi:0|1> [epoch_ins_M]
#   epoch_M      : window measured in DRAM accesses
#   epoch_ins_M  : window measured in instructions; when non-zero it replaces epoch_M
one_run() {
  local graph="$1" trials="$2" epoch="$3" l3kb="$4" l3assoc="$5" threads="$6" roi="$7"
  local epoch_ins="${8:-0}"
  local out="$TMP/run"
  rm -f "$out".*
  local roi_args=()
  [[ "$roi" == "1" ]] && roi_args=(-roi_begin hotskew_roi_begin -roi_end hotskew_roi_end)

  ( export OMP_NUM_THREADS="$threads"
    cd "$GAPBS_DIR" && \
    "$PIN" -t "$TOOL" -cache 1 -l1_kb 48 -l1_assoc 12 -l2_kb 2048 -l2_assoc 16 \
           -l3_kb "$l3kb" -l3_assoc "$l3assoc" -epoch "$epoch" -epoch_ins "$epoch_ins" \
           -dump_pages 0 "${roi_args[@]}" \
           -o "$out" -- "./$BENCH_KERNEL" -f "$graph" -n "$trials" \
  ) >/dev/null 2>&1

  if ! grep -q "^page_observations" "$out.summary.txt" 2>/dev/null; then
    echo "NA,NA,NA,NA,NA"
    return
  fi
  local mean p4 p16 p48 pages
  mean=$(awk '/^mean_unique_words/{print $2}' "$out.summary.txt")
  p4=$(awk '/^  4 /{print $3}' "$out.summary.txt")
  p16=$(awk '/^ 16 /{print $3}' "$out.summary.txt")
  p48=$(awk '/^ 48 /{print $3}' "$out.summary.txt")
  pages=$(awk '/^page_observations/{print $2}' "$out.summary.txt")
  echo "$mean,$p4,$p16,$p48,$pages"
}

hdr="mean_unique_words,p_le_4,p_le_16,p_le_48,page_observations"

sweep_scale() {
  echo "== dataset scale ==  (kernel=$BENCH_KERNEL, 1 trial, whole-run epoch)"
  local f="$OUTDIR/scale.csv"
  echo "graph_scale,footprint_mb,$hdr" > "$f"
  for s in 21 23 24 25; do
    local g="$GRAPH_DIR/kron-$s.sg"
    [[ -f "$g" ]] || continue
    local mb=$(( $(stat -c%s "$g") / 1048576 ))
    local r; r=$(one_run "$g" 1 0 36864 9 1 1)
    echo "$s,$mb,$r" | tee -a "$f"
  done
}

sweep_trials() {
  echo "== kernel invocations spanned by the measurement window =="
  local f="$OUTDIR/trials.csv"
  echo "trials,$hdr" > "$f"
  local g="$GRAPH_DIR/kron-${GRAPH_SCALE}.sg"
  for n in 1 2 4 8 16; do
    # roi=0: counters run across the whole process, as M5's always-on FPGA
    # counters do, so the window spans every trial.
    local r; r=$(one_run "$g" "$n" 0 36864 9 1 0)
    echo "$n,$r" | tee -a "$f"
  done
}

sweep_epoch() {
  echo "== measurement window length (millions of DRAM accesses) =="
  local f="$OUTDIR/epoch.csv"
  echo "epoch_M,$hdr" > "$f"
  local g="$GRAPH_DIR/kron-${GRAPH_SCALE}.sg"
  for e in 1 2 5 10 25 50 0; do
    local r; r=$(one_run "$g" 1 "$e" 36864 9 1 1)
    echo "$e,$r" | tee -a "$f"
  done
}

sweep_cache() {
  # The window here is deliberately measured in *instructions*, not DRAM accesses.
  #
  # With an access-based window, a smaller cache emits more DRAM accesses, so a fixed
  # count of them spans proportionally less execution -- the two effects cancel and
  # every LLC size reports an identical distribution. That is a real property, not a
  # bug (see docs/methodology.md §3), but it makes the axis uninformative.
  #
  # An instruction-based window is the time-proportional one, and matches how M5
  # sampled: their PAC daemon dumps every 10 ms of wall clock (m5_manager -s 10).
  # Under that window a bigger cache genuinely absorbs more traffic and fewer words
  # per page reach the controller.
  local epoch_ins="${CACHE_SWEEP_EPOCH_INS:-200}"
  echo "== LLC partition (M5's Intel CAT way masks), ${epoch_ins}M-instruction window =="
  local f="$OUTDIR/cache.csv"
  echo "llc_mb,llc_ways,$hdr" > "$f"
  local g="$GRAPH_DIR/kron-${GRAPH_SCALE}.sg"
  for spec in "4096 1" "16384 4" "36864 9" "61440 15"; do
    set -- $spec
    local r; r=$(one_run "$g" 1 0 "$1" "$2" 1 1 "$epoch_ins")
    echo "$(( $1 / 1024 )),$2,$r" | tee -a "$f"
  done
}

sweep_window_kind() {
  # Direct demonstration of the above: the same LLC sizes under both window kinds.
  echo "== window kind: DRAM-access-based vs instruction-based =="
  local f="$OUTDIR/window_kind.csv"
  echo "window_kind,llc_mb,$hdr" > "$f"
  local g="$GRAPH_DIR/kron-${GRAPH_SCALE}.sg"
  for spec in "4096 1" "61440 15"; do
    set -- $spec
    local r
    r=$(one_run "$g" 1 5 "$1" "$2" 1 1 0);   echo "dram_accesses_5M,$(( $1/1024 )),$r" | tee -a "$f"
    r=$(one_run "$g" 1 0 "$1" "$2" 1 1 200); echo "instructions_200M,$(( $1/1024 )),$r" | tee -a "$f"
  done
}

sweep_threads() {
  echo "== application thread count =="
  local f="$OUTDIR/threads.csv"
  echo "threads,$hdr" > "$f"
  local g="$GRAPH_DIR/kron-${GRAPH_SCALE}.sg"
  for t in 1 2 4 8; do
    local r; r=$(one_run "$g" 1 0 36864 9 "$t" 1)
    echo "$t,$r" | tee -a "$f"
  done
}

case "$AXIS" in
  scale)   sweep_scale ;;
  trials)  sweep_trials ;;
  epoch)   sweep_epoch ;;
  cache)   sweep_cache ;;
  threads) sweep_threads ;;
  window)  sweep_window_kind ;;
  all)     sweep_scale; sweep_trials; sweep_epoch; sweep_cache; sweep_threads
           sweep_window_kind ;;
  *)       die "unknown axis: $AXIS" ;;
esac

echo
echo "csv written under $OUTDIR"
