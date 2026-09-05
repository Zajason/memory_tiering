#!/usr/bin/env bash
# run_all_gapbs.sh -- profile every GAPBS kernel, in one or both load variants.
#
#   ./run_all_gapbs.sh [stock|userspace-load|both] [kernels...]
#
# Trial counts are per kernel, not global:
#   pr, sssp   reach maximal word coverage in a single invocation (PageRank sweeps
#              every edge), so extra trials cost hours under Pin and change nothing
#   bfs, cc    coverage grows with trials -- this is a real sensitivity, see
#              docs/methodology.md §7 -- so they get several
#   bc, tc     expensive per invocation; one each
#
# tc is superlinear in edge count and uses a smaller graph; the deviation is recorded
# in the results rather than hidden.

set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"

VARIANTS="${1:-both}"
shift || true
KERNELS=("${@:-bfs cc sssp pr bc tc}")
read -r -a KERNELS <<< "${KERNELS[*]}"

case "$VARIANTS" in
  stock)          VLIST=(stock) ;;
  userspace-load) VLIST=(userspace-load) ;;
  both)           VLIST=(stock userspace-load) ;;
  *) echo "first argument must be stock, userspace-load or both" >&2; exit 1 ;;
esac

trials_for() {
  case "$1" in
    bfs|cc) echo "${TRIALS_TRAVERSAL:-8}" ;;
    *)      echo 1 ;;
  esac
}
scale_for() {
  case "$1" in
    tc) echo "${TC_GRAPH_SCALE:-21}" ;;
    *)  echo "${GRAPH_SCALE:-23}" ;;
  esac
}

for v in "${VLIST[@]}"; do
  for k in "${KERNELS[@]}"; do
    echo "########## $k [$v] ##########"
    GAPBS_VARIANT="$v" \
    GAPBS_TRIALS="$(trials_for "$k")" \
    GRAPH_SCALE="$(scale_for "$k")" \
      timeout "${PER_KERNEL_TIMEOUT:-5400}" \
      "$REPO/experiments/run_hotskew.sh" "gapbs-$k" "${CONFIG:-spr-20t}" 2>&1 | tail -18
    echo
  done
done
echo "RUN_ALL_GAPBS_DONE"
