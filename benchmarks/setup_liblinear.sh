#!/usr/bin/env bash
# setup_liblinear.sh -- build LIBLINEAR (multicore) and fetch its training set.
#
# Liblinear is one of the twelve benchmarks behind M5's Figures 4 and 10, and one of
# the more interesting ones: the paper puts it in the "notable access sparsity" group
# alongside the graph traversals (Figure 4: P(<=25% of words) = 0.15).
#
# M5's env.sh points LIBLINEAR_PATH at Memtis' bench_dir copy of
# liblinear-multicore-2.47, which is upstream unmodified.
#
#   ./setup_liblinear.sh [dataset]
#
#   dataset: kdda (default, ~2.5 GB compressed) | url | rcv1
#
# The dataset is the reason this is a separate script from the GAPBS one: it is a
# large download from an academic host that is sometimes slow.

set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/../experiments/env.sh"

DATASET="${1:-kdda}"

# The upstream archive is named liblinear-multicore-<ver>.zip -- note the word order,
# which is the reverse of the directory name, and .zip rather than .tar.gz. The version
# also moves. Rather than hardcode it (a 404 that looks like a network problem), scrape
# the index page for the link and fall back to a known-good version.
BASE="https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/multicore-liblinear"
ARCHIVE="$(curl -fsL --retry 2 "$BASE/" 2>/dev/null \
           | grep -oiE 'liblinear-multicore-[0-9.]+\.zip' | head -1)"
: "${ARCHIVE:=liblinear-multicore-2.50.zip}"
URL="$BASE/$ARCHIVE"
echo ">> upstream archive: $ARCHIVE"

mkdir -p "$BENCH_ROOT"

if [[ ! -d "$LIBLINEAR_DIR" ]]; then
  echo ">> downloading $ARCHIVE"
  tmp="$BENCH_ROOT/$ARCHIVE"
  curl -fL --retry 3 -o "$tmp" "$URL" || die "download failed: $URL"
  command -v unzip >/dev/null || die "unzip not installed (sudo apt install unzip)"
  unzip -q -o "$tmp" -d "$BENCH_ROOT"
  # Unpacks to liblinear-multicore-<ver>; normalise the directory name.
  extracted="$(find "$BENCH_ROOT" -maxdepth 1 -type d -name "*liblinear*multicore*" | head -1)"
  [[ -n "$extracted" ]] || die "could not find the extracted liblinear directory"
  mv "$extracted" "$LIBLINEAR_DIR"
  rm -f "$tmp"
fi

# ROI markers around the solver. Without them the measurement is dominated by
# parsing the multi-gigabyte SVM-light text file, which streams densely over
# everything it touches and would report the workload as perfectly dense.
echo ">> installing ROI markers"
cp "$REPO/src/profiler/roi/hotskew_roi.h" "$LIBLINEAR_DIR/"
if ! grep -q hotskew_roi "$LIBLINEAR_DIR/train.c" 2>/dev/null; then
  python3 - "$LIBLINEAR_DIR/train.c" <<'PY'
import re, sys
path = sys.argv[1]
src = open(path).read()
if 'hotskew_roi' in src:
    sys.exit(0)
src = src.replace('#include "linear.h"', '#include "linear.h"\n#include "hotskew_roi.h"', 1)
# The solver call is the region of interest; everything before it is file parsing.
src = re.sub(r'(\n\s*)(model_\s*=\s*train\s*\(\s*&prob\s*,\s*&param\s*\)\s*;)',
             r'\1hotskew_roi_begin();\1\2\1hotskew_roi_end();', src, count=1)
open(path, 'w').write(src)
print("   train.c patched")
PY
else
  echo "   already patched"
fi

echo ">> building"
make -C "$LIBLINEAR_DIR" -j"$(nproc)"
[[ -x "$LIBLINEAR_DIR/train" ]] || die "build produced no train binary"
n=$(nm "$LIBLINEAR_DIR/train" | grep -c hotskew_roi || true)
[[ "$n" -ge 2 ]] || echo "   WARNING: no ROI symbols in train -- runs will profile the whole process"

mkdir -p "$LIBLINEAR_DIR/data"
case "$DATASET" in
  kdda) DURL="https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/binary/kdda.bz2" ;;
  url)  DURL="https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/binary/url_combined.bz2" ;;
  rcv1) DURL="https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/binary/rcv1_test.binary.bz2" ;;
  *)    die "unknown dataset: $DATASET" ;;
esac

if [[ ! -f "$LIBLINEAR_DIR/data/$DATASET" ]]; then
  echo ">> downloading $DATASET (this is large and the host is often slow)"
  curl -fL --retry 3 -o "$LIBLINEAR_DIR/data/$DATASET.bz2" "$DURL"
  echo ">> decompressing"
  bunzip2 -f "$LIBLINEAR_DIR/data/$DATASET.bz2"
fi

ls -lh "$LIBLINEAR_DIR/data/"
echo
echo "run with:  ./experiments/run_hotskew.sh liblinear"
