# Pin scalability: 31 October 2026

## User-directed stop and queue separation

The user authorized stopping the oversized twenty-thread TC control, preserving
its partial output, improving scalability and validating before retrying large
multithreaded experiments. The approximately fifty-hour attempt is interrupted,
not a completed result. It emitted 195 full 10M-event windows and a partial window
during termination. Neither these CDFs nor a termination-produced tool summary
qualify as completed evidence; campaign and manifest status gate publication.

The original directory is retained at
`results/fidelity-stage2-2026-10-28/footprint20-tc/attempt-1/`.
`campaign.json` records `multithread_hold: true`. The service now runs
`experiments/run_pin_fidelity_stage2.py --single-thread-only --tool ...` and
continues process PR/TC and nine-way PR/TC with the original instrument:

```text
SHA-256: a7276ee255ea5e74179fd22fff41ad4d7052520ea626339717b67032514a706a
Frozen path: /mnt/research/memory-tiering/profiler-builds/<SHA-256>/hotskew.so
```

The default `obj-intel64/hotskew.so` has not been rebuilt. The simulator service,
binary, configuration, guest disks and checkpoint protocol are unchanged.

## Candidate, not a new primary protocol

Build the candidate without replacing the baseline:

```bash
make -C src/profiler/pintool PIN_ROOT=/home/zajason/dev/advarch/pin OBJDIR=obj-intel64-scalable/
```

All performance options are opt-in and recorded in commands and summaries:

- `-local_bbl 1`: accumulate instruction totals per thread instead of taking the
  measurement lock at every basic block. Reject instruction-driven fast-forward,
  warm-up, length and instruction-window modes. Those require the legacy clock.
- `-sync_mode mutex`: test Pin's documented mutex API as an alternative to
  `PIN_LOCK`. This does not itself promise OS sleeping, fairness or a speedup.
- `-private_parallel 1`: calculate per-thread private-cache outcomes before
  acquiring the shared transaction lock. This is valid only for this model's
  independent private levels: there is no coherence or inclusive invalidation
  from the LLC. Shared LLC processing, paired access/fill/traffic recording,
  counter updates, limits and epoch transitions stay serialized together.

No asynchronous queues, dropped references, sampled accesses, sharded shared
cache model or relaxed window boundaries have been introduced. Retaining a
serialized shared transaction is necessary for the declared model, even if it
limits maximum speed. Multithreaded instrumentation still changes scheduling;
equivalent model semantics do not imply identical concurrent traces or CDFs.

## Validation

`experiments/validate_pin_scalability.py` runs separately from fidelity scoring.
It uses an external output directory, bounded child-process runtimes and fresh
attempt directories, never overwriting earlier checks.

1. A deterministic native read/write fixture must produce byte-identical epoch
   and full paired CSV files against the frozen tool under both event and
   reference windows, including final partials, ROI transitions and whole union.
2. A portable C++ replay test computes private outcomes out of global order but
   replays shared transactions in the same order. It requires identical memory
   event ordering and paired outputs, including writebacks and window boundaries.
3. An explicit rejection diagnostic gates unsupported instruction clocks. This
   Pin version can return exit code zero on an early tool-main return, so the
   guard check uses the diagnostic emitted before `PIN_StartProgram()`.
4. Small TC runs at 1/2/4/8/20 threads use two repetitions and audit completion,
   totals, populations, histogram consistency and unions for every completed run.
   Timing is end-to-end instrument-runtime wall time, not application speedup.
   Concurrent one-thread PR and simulator activity are not an isolated host setup.

Artifacts are under `/mnt/research/memory-tiering/profiler-validation/`.
Attempts 1 and 2 preserved exact-output passes but falsely failed the test harness's
initial exit-code assumption for the guard. Attempt 3 passed the corrected guard,
ten deterministic fixture cases and thirty audited small-input scaling runs.
It tests the local-BBL and mutex options before private-cache parallelism.
Attempt 4 adds the private-cache candidate and repeats the gates; all fourteen
exact-output checks and fifty audited scaling runs passed. Attempt 5 passes the
same fourteen checks and ten audited runs on a larger bounded scale-14 graph
(one repetition at one and twenty threads). Reports copied
under `results/pin-scalability-2026-10-31/` are small completed validation records,
not checkpoint files, traces or partial fidelity measurements.

The frozen candidate for attempts 4 and 5 has SHA-256
`6a24fae0dd3fbd7a61d9b0db1dc65e8bf8764bac65780aa85c46268d9eaf3941`,
stored under the same hash-addressed build directory as the baseline. Attempt 3's
earlier candidate hash is recorded in its report, but that binary was not frozen.

End-to-end seconds, not application speedups:

| Input / threads | Baseline | Local BBL | Mutex + local | Private + local | Mutex + private + local |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scale 12 / 1 | 1.367 | 1.266 | 1.267 | 1.291 | 1.267 |
| Scale 12 / 2 | 2.343 | 1.843 | 1.868 | 1.867 | 1.767 |
| Scale 12 / 4 | 3.220 | 2.268 | 2.293 | 2.294 | 2.293 |
| Scale 12 / 8 | 5.097 | 3.295 | 3.244 | 3.245 | 3.170 |
| Scale 12 / 20 | 8.004 | 5.051 | 5.000 | 4.673 | 5.051 |
| Scale 14 / 1 | 3.421 | 2.870 | 2.820 | 2.969 | 2.971 |
| Scale 14 / 20 | 52.777 | 22.763 | 22.300 | 24.100 | 24.373 |

Scale-12 entries are medians of two repetitions; scale-14 entries are single
observations. Removing BBL lock acquisitions improves the larger twenty-thread
case by about 2.32x, but twenty threads remain much slower than one. The private
cache option helps the tiny twenty-thread case but loses to local BBL alone on
the larger case. The mutex alternative offers no consistent decisive gain.
These are preliminary, non-isolated engineering timings, not reliable large-TC
runtime predictions or evidence of identical concurrent CDFs. No new favorable
curve has replaced the common-protocol primary comparison.

## Deployment gate

Do not clear the hold or launch another large twenty-thread TC merely because a
tiny case is faster. First require all correctness gates, repeated scaling,
a bounded larger-input test, a frozen candidate hash and explicit versioned
commands. Preserve unsuccessful lock alternatives. Rerun affected multithreaded
controls consistently as a new instrument-version control series, never silently
replace individual favorable workloads or mix versions into the primary figure.
The current validation script always records `deployment_approved: false`;
passing smoke tests is not automatic deployment approval.
