#!/usr/bin/env bash
# run_hotskew.sh -- profile one benchmark under the hotskew pintool.
#
#   ./run_hotskew.sh <benchmark> [config]
#
#   benchmark : gapbs-bc | gapbs-bfs | gapbs-cc | gapbs-pr | gapbs-sssp | gapbs-tc
#               liblinear | redis
#   config    : a name from configs/ without the .env suffix (default: chosen to
#               match the workload class, as M5 did with Intel CAT)
#
# Results land in results/<config>/<benchmark>.{summary.txt,epochs.csv,pages.bin}

set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"

BENCH="${1:-}"
[[ -n "$BENCH" ]] || { sed -n '2,14p' "$0" | sed 's/^# \?//'; exit 1; }

# M5 gave each workload class a different slice of LLC. Default to the matching one.
default_config() {
  case "$1" in
    gapbs-*|liblinear) echo "spr-20t" ;;
    redis)             echo "spr-1t"  ;;
    spec-*)            echo "spr-8t"  ;;
    *)                 echo "spr-20t" ;;
  esac
}
CONFIG="${2:-$(default_config "$BENCH")}"
CFG_FILE="$REPO/configs/$CONFIG.env"
[[ -f "$CFG_FILE" ]] || die "no such config: $CFG_FILE"

CACHE_OFF=0
# shellcheck disable=SC1090
source "$CFG_FILE"

check_prereqs

# The GAPBS variant changes what is measured, not just how, so it gets its own
# results directory rather than silently overwriting the other one.
SUFFIX=""
[[ "${GAPBS_VARIANT:-stock}" == "userspace-load" ]] && SUFFIX="-ul"
OUTDIR="$RESULTS_ROOT/$CONFIG$SUFFIX"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/$BENCH"

# Assemble the cache knobs.
if [[ "$CACHE_OFF" == "1" ]]; then
  CACHE_ARGS=(-cache 0)
else
  CACHE_ARGS=(-cache 1
              -l1_kb "$L1_KB" -l1_assoc "$L1_ASSOC"
              -l2_kb "$L2_KB" -l2_assoc "$L2_ASSOC"
              -l3_kb "$L3_KB" -l3_assoc "$L3_ASSOC")
fi

COMMON=(-epoch "$EPOCH_M" -dump_pages "$DUMP_PAGES" -tag "$BENCH" -o "$OUT"
        -roi_begin hotskew_roi_begin -roi_end hotskew_roi_end)

export OMP_NUM_THREADS="$HOST_THREADS"

run_pin() { # run_pin <workdir> <cmd...>
  local wd="$1"; shift
  echo "=== $BENCH [$CONFIG${SUFFIX}]  threads=$HOST_THREADS epoch=${EPOCH_M}M \
variant=${GAPBS_VARIANT:-stock} ==="
  echo "    $*"
  local log="$OUT.run.log"
  ( cd "$wd" && /usr/bin/time -f "    wall %e s   maxrss %M KB" \
      "$PIN" -t "$TOOL" "${CACHE_ARGS[@]}" "${COMMON[@]}" -- "$@" ) >"$log" 2>&1
  local rc=$?
  grep -vE "^\[hotskew\] ROI hooked" "$log" | tail -20
  # A benchmark that died still leaves a summary file behind, so check explicitly
  # rather than trusting that output exists.
  if [[ $rc -ne 0 ]]; then
    echo "!! the benchmark exited with status $rc -- results are not usable" >&2
    echo "!! full log: $log" >&2
    return 1
  fi
  if ! grep -q "^[[:space:]]*\[hotskew\] ROI hooked" "$log" && grep -q "roi_begin" <<<"${COMMON[*]}"; then
    echo "!! no ROI symbol matched -- the binary is probably missing the markers" >&2
    echo "!! rebuild it with benchmarks/patches/*.patch applied" >&2
    return 1
  fi
  return 0
}

case "$BENCH" in
  gapbs-*)
    KERNEL="${BENCH#gapbs-}"
    # sssp is the one kernel that needs edge weights, and GAPBS refuses a plain .sg
    # for it ("*.sg not allowed for weighted graphs"). Picking the wrong extension
    # here is a silent-looking failure, so it is spelled out rather than guessed.
    case "$KERNEL" in
      sssp) GRAPH="$GRAPH_DIR/kron-$GRAPH_SCALE.wsg" ;;
      *)    GRAPH="$GRAPH_DIR/kron-$GRAPH_SCALE.sg"  ;;
    esac
    [[ -f "$GRAPH" ]] || die "missing $GRAPH -- run benchmarks/setup_gapbs.sh"
    [[ -x "$GAPBS_DIR/$KERNEL" ]] || die "missing $GAPBS_DIR/$KERNEL"
    # GAPBS_TRIALS: how many kernel invocations the epoch spans. See
    # docs/methodology.md -- for the traversal kernels this is a first-order knob,
    # because one BFS from one source visits only part of the graph.
    run_pin "$GAPBS_DIR" "./$KERNEL" -f "$GRAPH" -n "${GAPBS_TRIALS:-1}"
    ;;

  liblinear)
    [[ -x "$LIBLINEAR_DIR/train" ]] || die "missing liblinear -- run benchmarks/setup_liblinear.sh"
    DATA="$LIBLINEAR_DIR/data/kdda"
    [[ -f "$DATA" ]] || die "missing training set $DATA -- run benchmarks/setup_liblinear.sh"
    # -s 6 = L1-regularised logistic regression, the solver Memtis/M5 use.
    run_pin "$LIBLINEAR_DIR" ./train -s 6 -m "$HOST_THREADS" -e 0.01 "$DATA"
    ;;

  redis)
    die "redis is driven by a client; use experiments/run_redis.sh"
    ;;

  *)
    die "unknown benchmark: $BENCH"
    ;;
esac

echo
if [[ -f "$OUT.summary.txt" ]]; then
  sed -n '/^# M5 Figure 4/,/^# P(page has at least/p' "$OUT.summary.txt"
  grep -E "^(mean_unique_words|top4_word_share|llc_miss_ratio|epochs|page_observations)" "$OUT.summary.txt"
else
  echo "no summary produced -- check the output above"
fi
