#!/usr/bin/env bash
# setup_gapbs.sh -- fetch, patch and build GAPBS, then generate the input graphs.
#
# GAPBS is six of the twelve benchmarks behind M5's Figures 4 and 10 (bc, bfs, cc,
# pr, sssp, tc). M5 took its copy from Memtis' bench_dir; we use upstream, which is
# the same code.
#
#   ./setup_gapbs.sh [scales...]     (default: 23 25)
#
# Disk: a kron-25 graph pair is ~13 GB. kron-23 is ~3 GB. Check before running.

set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/../experiments/env.sh"

SCALES=("${@:-23 25}")
read -r -a SCALES <<< "${SCALES[*]}"

mkdir -p "$BENCH_ROOT"

if [[ ! -d "$GAPBS_DIR" ]]; then
  echo ">> cloning GAPBS"
  git clone --depth 1 https://github.com/sbeamer/gapbs.git "$GAPBS_DIR"
fi

# The ROI markers. Without them the measurement includes graph construction, which
# streams densely over the whole CSR and washes out the access pattern we care about.
echo ">> installing ROI markers"
cp "$REPO/src/profiler/roi/hotskew_roi.h" "$GAPBS_DIR/src/"
if ! grep -q hotskew_roi "$GAPBS_DIR/src/benchmark.h"; then
  git -C "$GAPBS_DIR" apply "$REPO/benchmarks/patches/gapbs-roi.patch"
  echo "   patch applied"
else
  echo "   already patched"
fi

echo ">> building"
make -C "$GAPBS_DIR" -j"$(nproc)"

for k in bc bfs cc pr sssp tc converter; do
  [[ -x "$GAPBS_DIR/$k" ]] || die "build produced no $k"
done
for k in bc bfs cc pr sssp tc; do
  n=$(nm "$GAPBS_DIR/$k" | grep -c hotskew_roi || true)
  [[ "$n" -ge 2 ]] || die "$k has no ROI symbols -- the patch did not take effect"
done
echo "   all six kernels built with ROI markers"

mkdir -p "$GRAPH_DIR"
for s in "${SCALES[@]}"; do
  # Kronecker graphs, GAPBS' own generator: 2^s vertices, average degree 16.
  # This is the standard GAP input and matches what Memtis/M5 used.
  if [[ ! -f "$GRAPH_DIR/kron-$s.sg" ]]; then
    echo ">> generating kron-$s.sg (unweighted; bc bfs cc pr tc)"
    "$GAPBS_DIR/converter" -g "$s" -b "$GRAPH_DIR/kron-$s.sg"
  fi
  # sssp needs edge weights and GAPBS rejects a plain .sg for it.
  if [[ ! -f "$GRAPH_DIR/kron-$s.wsg" ]]; then
    echo ">> generating kron-$s.wsg (weighted; sssp)"
    "$GAPBS_DIR/converter" -g "$s" -wb "$GRAPH_DIR/kron-$s.wsg"
  fi
done

echo
echo "graphs in $GRAPH_DIR:"
ls -lh "$GRAPH_DIR"
