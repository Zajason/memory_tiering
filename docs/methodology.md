# Measurement methodology

The primary target is **M5 Figure 4**: the CDF of distinct 64-byte lines observed
within each 4 KiB page. Figure 3 instead compares ANB/DAMON page selection with PAC;
we have not reproduced that experiment. Coverage measures sparsity, not frequency.

See [the October audit](audit-2026-10.md) for corrections to historical results.
The subsequent [dataset/window control](reproduction-followup.md) tests Google+
(not web-Google) on BC/SSSP, with both raw-reference and memory-event windows.
All settings are reported; no window is selected by fitting M5's curve.
The [uniform-window campaign](uniform-windows.md) applies the memory-event
definition to all six kernels, alongside an all-synthetic input control.

## Observation streams

M5 places PAC/WAC between the CXL IP and memory controllers (section 3). Pin sees
user-space memory instructions before CPU cache filtering. The professor's
access-based extension deliberately measures this earlier point.

| Stream | Counted event |
|---|---|
| Demand accesses | Predicated memory operands, split into overlapping 64-byte lines |
| Demand misses / fills | Demand references missing every modeled cache level |
| Total modeled traffic | Demand fills plus dirty LLC evictions |

Read-modify-write operands count once as write-capable operands. A split operand
counts once per overlapping line. This convention affects frequency, not a coverage
mask within the same window. Software prefetch hints and instruction fetches are
excluded. Kernel execution and hardware prefetches are absent. Callbacks execute
before instructions; this is not a hardware retired-load trace.
Active gather/scatter memory-vector instructions are rejected because their
noncontiguous addresses need separate instrumentation. Results cannot silently
include only one address from such an instruction.

The paired mode (`-paired 1`) counts all three streams in **one execution**. It
retains bitmasks, not a full address trace. Comparing 10M accesses in one execution
interval to 10M misses in a different interval would confound the experiment.

## Windows and populations

The runner default and initial audited experiment use 10 million **line-operand references** per window
(`-epoch_refs 10`). All streams reset at the same boundary. The final partial
window is included and identifiable in per-epoch records. A separate whole-ROI
union counts each touched page once. Neither interval is fitted to M5.

The uniform-window follow-up explicitly sets `--epoch-traffic 10`: 10 million
**modeled memory events** (fills plus dirty writebacks), with `epoch_refs=0`.
This is a different experimental clock, not a new definition of an access.
All three streams still reset together. A workload with fewer than 10M memory
events contributes one final partial window, equal to its whole-ROI observation.
There is no evidence yet that either local clock is the one used for M5 Figure 4.

Let U(p,e,S) be the number of distinct lines in page p, window e, stream S:

`F_S(N) = count((p,e): 1 <= U(p,e,S) <= N) / count((p,e): U(p,e,S) >= 1)`.

Every page-window pair has equal weight. A page touched in ten windows contributes
ten observations; in the whole-ROI distribution it contributes one. Do not take an
unweighted average of per-window CDFs with different page counts.

The access and miss streams can touch different page sets. We therefore also plot
both over the **same fill-touched pages**. CSVs additionally contain the
access-touched population, including pages with zero misses. This separates
filtering from denominator changes. Allocated pages never touched by an observed
event are absent; Pin does not enumerate allocations.

With initially empty caches, no prefetches and no unobserved warming, every first
demand touch causes a fill. The whole-ROI unions should then agree even if event
counts differ greatly. Setup-warmed runs can legitimately break this equality.

Longer nested windows only add bits for a fixed page. They do not necessarily make
every page dense or make a pooled CDF monotonic: its page population and partial
windows also change. Smaller caches and fixed miss-count windows do **not** obey
an exact cancellation law. Instruction counts are not elapsed time.

M5 describes 128 MiB WAC regions and multiple collection strategies. We have not
established Figure 4's exact reset interval, region schedule, or population
treatment. The daemon's 10 ms polling interval does not establish these. The ten
random execution points in section 4.1 describe Figure 3; they cannot be assigned
to Figure 4 without further evidence.

## Cache approximation

The filter uses private L1D/L2 and a shared LLC: write-allocate, writeback, LRU,
non-inclusive. Demand stores dirty L1; lower read fills stay clean until a dirty
eviction reaches them. Every eviction is propagated, including an L2 eviction
caused by an L1 writeback. A full-line writeback allocating in a lower cache does
not need another memory read.

There is no coherence, hardware prefetching, physical translation, slice hashing,
out-of-order execution or memory timing. Private caches are per software thread,
not scheduled physical core. Locking instrumentation state prevents data races;
it does not simulate coherent multicore ordering.

The legacy `spr-20t` configuration uses 9 LLC ways / 36 MiB, matching mask
`0x7FC0` in the artifact. Table 3 reports 10 ways; `spr-paper` uses 10 ways /
40 MiB. Matching modeled capacity and ways does not reproduce real CAT behavior,
physical indexing or replacement exactly. Both choices are explicit controls.

Omitting prefetching establishes no general density bound. Prefetches can add
traffic, replace demand fills, and change evictions and window boundaries.

Translation preserves offsets (`VA[11:0] = PA[11:0]`). This preserves line position
inside a page; it does not establish the same miss stream or physical page identity
under virtual aliases, remapping or reuse.

## Workload fidelity

| Parameter | M5 | Local paired experiment |
|---|---|---|
| GAPBS graphs | Resized Twitter for BFS/CC/PR/TC; directed Google for BC/SSSP | Existing synthetic kron-23 |
| Threads | 20 for graph workloads | 1 |
| Trials | Figure-specific invocation unresolved | 1 |
| Scope | Exact Figure 4 collection unresolved | Stock timed-kernel ROI |
| Initial cache state | Real machine | Cold at first ROI; separate setup-warmed controls |
| Addresses | Physical device requests | Virtual demand operands and modeled filtering |
| Liblinear | 2.47, KDD2012 | Historical 2.50/KDD2010 is not equivalent |
| Redis | 6.0.16, YCSB-A | Historical 7.2.5/custom client is approximate |

The `userspace-load` patch adds a staging-buffer copy. Its harness includes setup;
stock GAPBS defaults to kernel-only ROI. This changes both traffic and scope. It is
a visibility sensitivity experiment, not a transparent reconstruction of kernel
traffic. The read(2)/memcpy test demonstrates Pin's blind spot, not how many real
DRAM requests every kernel copy must cause.

Full-system gem5 observes physical requests and kernel activity, but changes cache,
CPU, OS, placement and measurement scope too. Pin-versus-gem5 deltas do not isolate
kernel visibility. Historical simulator outputs require separate completion
evidence; a per-epoch summary file is not proof the workload finished.

## Analysis and verification

- Report all five thresholds (4, 8, 16, 32, 48). State maximum absolute difference
  and approximate digitization uncertainty. Prose percentages are rounded.
- The complement of P(U >= 48) is P(U <= 47), not P(U <= 48).
- Window fitting is exploratory. A fit cannot identify the original interval or
  establish why two experiments differ. Require complete dumps and compatible ROI
  boundaries before merging windows.
- Disk records are 164 bytes. Saturated 16-bit word counts preserve coverage masks
  but compromise frequency rankings. Saturation is reported. Capped dumps cannot
  support whole-run reconstruction.
- Placement and latency models are exploratory heuristics, not M5 implementations.
  Historical estimates used future page membership and are withdrawn. A serial
  memory-cost ratio is neither measured application speedup nor a proven bound.
- `make audit-test` checks dirty evictions, clean fills, populations, mask union,
  thresholds, incomplete dumps and previous-window-only placement.
- The runner records commands, binary/tool hashes, input identity, settings, return
  codes and completion status. Plotting excludes interrupted and limited runs.

```bash
make -C src/profiler/pintool PIN_ROOT="$HOME/dev/advarch/pin"
make audit-test
python3 experiments/run_paired.py
./.venv/bin/python src/analysis/plot_paired.py
```

Use a different `--out` for controls or reruns. Retaining partial statistics does
not resume execution after reboot; real checkpointing is a separate capability.
