# Shared paths and defaults. Sourced by everything in experiments/.
# Override any of these from your shell before running.

REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

: "${PIN_ROOT:=$HOME/dev/advarch/pin}"
: "${BENCH_ROOT:=$REPO/bench}"
: "${RESULTS_ROOT:=$REPO/results}"

PIN="$PIN_ROOT/pin"
TOOL="$REPO/src/profiler/pintool/obj-intel64/hotskew.so"

# Two GAPBS builds, differing only in who copies the graph during loading.
#
#   bench/gapbs     stock: file.read(), so the kernel performs the copy and Pin
#                   cannot see it. Measures the application's own access pattern.
#   bench/gapbs-ul  patched: the copy goes through a user-space staging buffer, so
#                   the destination writes are visible. Measures what a memory
#                   controller -- and therefore M5's PAC/WAC -- would have seen.
#
# The difference is large and it is the main reason a naive Pin reproduction of M5's
# Figure 4 comes out too sparse. See docs/methodology.md §3b.
#
# GAPBS_VARIANT=stock|userspace-load
: "${GAPBS_VARIANT:=stock}"
case "$GAPBS_VARIANT" in
  stock)          GAPBS_DIR="$BENCH_ROOT/gapbs" ;;
  userspace-load) GAPBS_DIR="$BENCH_ROOT/gapbs-ul" ;;
  *) echo "GAPBS_VARIANT must be stock or userspace-load" >&2; exit 1 ;;
esac
# Graphs are shared between the two builds; they are large and identical.
GRAPH_DIR="$BENCH_ROOT/gapbs/graphs"
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
