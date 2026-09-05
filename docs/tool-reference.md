# `hotskew` pintool — reference

```
$PIN_ROOT/pin -t src/profiler/pintool/obj-intel64/hotskew.so [knobs] -- <app> [args]
```

## Knobs

### Output

| Knob | Default | Meaning |
|---|---|---|
| `-o <prefix>` | `hotskew` | writes `<prefix>.summary.txt`, `.epochs.csv`, `.pages.bin` |
| `-tag <name>` | — | label recorded in the output |
| `-dump_pages 0\|1` | `1` | write raw per-page records (needed for top-K analysis) |
| `-dump_min <n>` | `1` | only dump pages with at least `n` accesses in the epoch |

### Cache model

| Knob | Default | Meaning |
|---|---|---|
| `-cache 0\|1` | `1` | `1` = count the LLC miss stream (PAC/WAC semantics); `0` = count every load/store |
| `-l1_kb`, `-l1_assoc` | 48, 12 | L1d, per thread — Sapphire Rapids geometry |
| `-l2_kb`, `-l2_assoc` | 2048, 16 | L2, per thread |
| `-l3_kb`, `-l3_assoc` | 61440, 15 | LLC, shared. Set `assoc` to the granted CAT ways to model a partition |
| `-count_wb 0\|1` | `1` | count dirty LLC writebacks as DRAM accesses (PAC snoops them too) |

The number of sets must come out a power of two: `l3_kb*1024 / (64 * l3_assoc)`. Real
geometries cooperate — 60 MB / 15-way gives exactly 65536 sets, and every CAT
partition of it keeps that set count because CAT partitions by way. A bad geometry is
rejected at startup rather than silently rounded.

### Measurement window

| Knob | Default | Meaning |
|---|---|---|
| `-epoch <M>` | 50 | close the window every M million **DRAM accesses**; `0` = one window for the whole run |
| `-epoch_ins <M>` | 0 | close the window every M million **instructions** (time-proportional); overrides `-epoch` |
| `-max_epochs <n>` | 0 | stop after n epochs; `0` = unlimited |
| `-ff <M>` | 0 | skip M million instructions before doing anything |
| `-warmup <M>` | 0 | M million instructions warming the caches without counting |
| `-len <M>` | 0 | stop profiling after M million instructions; `0` = to completion |

**The window is not a detail.** Unique-word coverage per page only ever grows, so a
long enough window makes every page look dense. Always report the window length *and
kind* with any sparsity number — see [methodology §3](methodology.md#3-why-epochs-are-mandatory-the-most-important-thing-in-this-document).

### Region of interest

| Knob | Default | Meaning |
|---|---|---|
| `-roi_rtn <name>` | — | profile inside this routine only (enable on entry, disable on return) |
| `-roi_begin <name>` | — | routine whose entry starts profiling |
| `-roi_end <name>` | — | routine whose entry stops profiling |
| `-roi_epoch 0\|1` | `1` | close the epoch when the ROI is left, so one epoch never spans two invocations |

Names are matched as **substrings of the symbol name**, so mangled C++ names work
without demangling. The tool prints `[hotskew] ROI hooked: <name>` for each match —
if no such line appears, nothing was hooked and the whole process is being profiled.

Use the markers in `src/profiler/roi/hotskew_roi.h` (`hotskew_roi_begin` /
`hotskew_roi_end`) with `-roi_begin`/`-roi_end`.

## Output files

### `<prefix>.summary.txt`

Human-readable. Contains the run configuration, the Figure 4 CDF at
$N \in \{4,8,16,32,48\}$, the full 65-bin unique-word histogram, and the log2
histogram of accesses per page (Figure 10).

If a run recorded nothing, this file says `STATUS NO DATA` and lists the likely
causes instead of printing a CDF over an empty population. A table of zeros reads
exactly like a very sparse result, which is how a failed run gets mistaken for a
finding.

### `<prefix>.epochs.csv`

One row per epoch: `epoch, pages, accesses, mean_unique_words, p_le_4, p_le_8,
p_le_16, p_le_32, p_le_48`. Useful for seeing whether the distribution is stable
across the run or drifting between phases.

### `<prefix>.pages.bin`

Raw records, little-endian, packed, 160 bytes each:

```
uint32  epoch
uint64  page_number          (byte address >> 12)
uint64  reads
uint64  writes
uint64  touched_mask         bit w set iff 64 B word w was accessed
uint16  word_counts[64]
```

Read with `src/analysis/hotskew.py`:

```python
import hotskew as H
run = H.load_pages("results/spr-20t/gapbs-bfs.pages.bin", tag="gapbs-bfs")

run.figure4_cdf()                 # M5 Figure 4, all touched pages
run.figure4_cdf(top_k=10000)      # ...restricted to the pages a policy would migrate
run.top_word_share(4)             # share of accesses in each page's 4 hottest words
run.wasted_migration_bytes()      # fraction of a migrated 4 KB page never touched
```

The top-K restriction is the one the paper does not plot and the one a migration
policy actually experiences. For graph traversals the two differ sharply.

## Cost

About 40× slowdown on the profiled region, and 160 bytes of counter state per touched
page per epoch — roughly 160 MB for a 4 GB working set. Outside the ROI the overhead
is a basic-block counter and an inlined predicate, so fast-forwarding through setup is
cheap.

## Recipes

```bash
# Faithful PAC/WAC measurement of a GAPBS kernel, M5's 20-thread LLC partition
pin -t hotskew.so -l3_kb 36864 -l3_assoc 9 -epoch 10 \
    -roi_begin hotskew_roi_begin -roi_end hotskew_roi_end \
    -o out/bfs -- ./bfs -f kron-23.sg -n 1

# What a naive Pin tracer would report instead, for comparison
pin -t hotskew.so -cache 0 -epoch 10 \
    -roi_begin hotskew_roi_begin -roi_end hotskew_roi_end \
    -o out/bfs-raw -- ./bfs -f kron-23.sg -n 1

# Time-proportional window, so LLC size actually matters (see methodology §3)
pin -t hotskew.so -l3_kb 4096 -l3_assoc 1 -epoch_ins 200 \
    -o out/bfs-small-llc -- ./bfs -f kron-23.sg -n 1

# Skip a long setup phase without ROI markers in the binary
pin -t hotskew.so -ff 20000 -warmup 500 -len 5000 -o out/x -- ./app
```
