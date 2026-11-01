# Profiler bottleneck: bounded engineering result

## Decision

The six-case fixed-input study completed on 1 November 2026. Synchronization is
the dominant sampled twenty-thread CPU cost in both frozen instruments, even
after local-BBL accounting. This identifies the next engineering problem; it
does **not** approve a redesign, another input, a longer budget or a large run.
`deployment_approved` remains false and `multithread_hold` remains true.

The [predeclared protocol](pin-bottleneck-protocol.md) reused the existing
denominator-eight Twitter subset and unchanged tools. Six cases only, each capped
at 40 seconds, ran under the ten-minute/2-GiB service limit. The service exited
successfully. Both one-thread applications completed, returned 957,682 triangles,
passed paired audits and produced byte-identical paired/epoch CSVs. All four
twenty-thread captures reached their planned cutoff and remain interrupted
applications, not completed fidelity measurements. No study processes remain.

## CPU attribution

Percentages below use total sampled user CPU period, retaining unknown/JIT code.
They are **not percentages of wall time** or lock-wait latency. All six perf
reports record zero lost samples. Twenty-thread order was baseline/local-BBL/
local-BBL/baseline; the table retains each repetition rather than pooling away
variation.

| Threads / instrument | Samples | LockInternal | All named synchronization | Memory callback | Unknown/JIT |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 / baseline | 2,879 | 15.28% | 37.37% | 16.74% | 19.56% |
| 1 / local BBL | 2,186 | 9.79% | 20.91% | 29.83% | 14.41% |
| 20 / baseline A | 77,077 | 89.22% | 99.42% | 0.23% | 0.07% |
| 20 / local BBL A | 77,248 | 89.77% | 99.19% | 0.43% | 0.11% |
| 20 / local BBL B | 77,299 | 89.63% | 99.27% | 0.40% | 0.09% |
| 20 / baseline B | 77,281 | 89.83% | 99.45% | 0.21% | 0.07% |

The memory callback contains inlined work, so it is not a pure cache-model cost.
Observer/epoch symbols account for 10.84/13.54% in the one-thread pair, but only
0.03--0.09% in twenty-thread prefixes. This does not show that their absolute
cost disappeared: contention changes progress and the denominator. It does show
that optimizing observer arithmetic alone is not the demonstrated dominant
twenty-thread CPU opportunity in these captures.

## Lock-path evidence

Inspection of the frozen candidate's machine code shows `PIN_GetLock` calling
`OS_MutexLock`, while `PIN_MutexLock` jumps to that **same backend**. Their release
APIs likewise reach `OS_MutexUnlock`. `OS_MutexLock` reaches `LockInternal`, whose
retry loop contains atomic compare/exchange, a branch, `pause`, and a back edge.
In candidate twenty-thread capture A, 92.82% of the samples *within LockInternal*
are attributed to the branch immediately after compare/exchange, and 6.02% to
the loop back edge. Sampling skid prevents exact per-instruction cycle claims,
but the concentration in the acquisition retry loop supports a contention
diagnosis, not simply an expensive function name.

This explains why changing the public Pin lock API alone was not a convincing
solution in this frozen build. It is not a claim about every Pin version or
that the wrappers have identical overhead. The shared measurement transaction
still takes a lock on memory callbacks. That is the leading source-level
hypothesis, but frame-pointer callchains did not reliably recover callers or
lock-object identity. We cannot assign every synchronization sample specifically
to the measurement lock, or split spinning CPU from blocked wall time precisely.
TLS lookup also has visible one-thread cost; it is not established as the
dominant twenty-thread bottleneck.

## Provenance and limits

The [small derived report](../results/pin-bottleneck-2026-11-01/study.json)
records commands, tool/input fingerprints, sampling environment, raw-symbol
hashes, sample counts, cutoffs and audit results. The
[bounded disassembly/annotation evidence](../results/pin-bottleneck-2026-11-01/lock-evidence.txt)
is included separately. Raw perf data and interrupted outputs remain outside
the repository in `/mnt/research/memory-tiering/profiler-bottleneck/2026-11-01-attempt-1`.

The original capture classified `LockInternal`/`UnlockInternal` as other
tool-linked code. Derived classification version 2 corrects that after symbol
inspection, records both source and analysis hashes, and leaves the capture
unchanged. No workloads were rerun to make the categories look stronger.
Reproduce the derived JSON with:

```bash
.venv/bin/python src/analysis/publish_pin_bottleneck.py \
  --source /mnt/research/memory-tiering/profiler-bottleneck/2026-11-01-attempt-1
```

These are user CPU-clock samples at 99 Hz, not hardware cache misses, measured
application speedup or full held-input cost. Sampling perturbs timing, the
simulator continued concurrently, unknown/JIT samples remain, and the short
prefixes perform different amounts of work. The proxy remains largely
LLC-resident. No pilot curve enters the primary fidelity figure; neither the
M5 target nor our fidelity plots were changed by this engineering study.

## Before any redesign

Stop this bounded effort here. A subsequent explicit engineering decision should
address the serialized shared measurement transaction, with a written ordering
contract before implementation: shared-LLC access order, dirty propagation,
measurement-window boundaries and epoch snapshots must remain auditable.
Buffering, batching or a different synchronization mechanism cannot simply be
assumed equivalent. Require deterministic exact-output tests and the declared
audited 1/2/4/8/20-thread scaling gate before considering representative cost or
deployment. Do not implement speculative alternatives under this study, resize
another input, or tune any setting for closer M5 bars. The existing simulator
queue continues separately and unchanged.
