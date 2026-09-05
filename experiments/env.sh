# Shared paths and defaults. Sourced by everything in experiments/.
# Override any of these from your shell before running.

REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

: "${PIN_ROOT:=$HOME/dev/advarch/pin}"
: "${BENCH_ROOT:=$REPO/bench}"
: "${RESULTS_ROOT:=$REPO/results}"

PIN="$PIN_ROOT/pin"
TOOL="$REPO/src/profiler/pintool/obj-intel64/hotskew.so"

GAPBS_DIR="$BENCH_ROOT/gapbs"
GRAPH_DIR="$GAPBS_DIR/graphs"
LIBLINEAR_DIR="$BENCH_ROOT/liblinear-multicore"
REDIS_DIR="$BENCH_ROOT/redis"
YCSB_DIR="$BENCH_ROOT/ycsb"

# Measurement defaults.
#
# EPOCH_M -- millions of DRAM accesses per measurement epoch. This is the single
#   most consequential knob in the whole setup. An epoch is the window over which
#   "unique words touched in this page" is counted, and that count only grows, so a
#   long enough epoch makes every page look dense no matter what the workload does.
#   M5's hardware has the same property and they handle it the same way: WAC's 4-bit
#   counters are read and reset periodically, and Figure 4's data comes from bounded
#   sampling windows, not from whole runs.
#
#   50M DRAM accesses at ~3 GB/s of miss traffic is on the order of a second of real
#   execution -- comparable to the interval a tiering daemon would act on, which is
#   the timescale the question is actually about.
: "${EPOCH_M:=50}"

# GAPBS graph scale. kron-25 is ~4.3 GB resident, giving roughly the working-set to
# LLC ratio M5 had (their datasets were reduced to <8 GB against a 36 MB partition).
: "${GRAPH_SCALE:=25}"

# Threads for the benchmark itself. Default 1: see docs/methodology.md,
# "Why the headline runs are single-threaded".
: "${HOST_THREADS:=1}"

# Dump per-page raw records? Needed for the top-K-restricted analysis and for
# Figure 10 at full resolution. Costs ~160 bytes per touched page per epoch.
: "${DUMP_PAGES:=1}"

have() { command -v "$1" >/dev/null 2>&1; }

die() { echo "error: $*" >&2; exit 1; }

check_prereqs() {
  [[ -x "$PIN"  ]] || die "no pin binary at $PIN (set PIN_ROOT)"
  [[ -f "$TOOL" ]] || die "pintool not built. Run: make -C $REPO/src/profiler/pintool PIN_ROOT=$PIN_ROOT"
}
