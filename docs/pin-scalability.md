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

### Repeated larger-input check

Attempt 6 repeats scale 14 at all five thread counts with the same frozen
candidate. All fourteen exact-output fixture cases, the instruction-clock guard
and fifty completed scaling runs passed. Every scaling output passed the paired
histogram audit. Median seconds over two repetitions:

| Threads | Baseline | Local BBL | Mutex + local | Private + local | Mutex + private + local |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 3.395 | 2.869 | 2.820 | 2.994 | 2.968 |
| 2 | 7.803 | 5.473 | 5.250 | 5.149 | 5.174 |
| 4 | 13.444 | 7.402 | 6.976 | 6.924 | 7.003 |
| 8 | 25.679 | 12.838 | 13.014 | 12.463 | 12.388 |
| 20 | 48.559 | 21.829 | 24.606 | 22.978 | 23.734 |

The simplest local-BBL option again improves twenty-thread instrumentation
runtime (about 2.22x), but twenty threads still take about 7.61x the optimized
one-thread time. This supports removing unnecessary instruction-counter locking,
not a claim of scalable parallel profiling. More complicated locking/private
options do not consistently improve on it. Baseline and candidate configurations
ran sequentially in fixed order while the original Pin PR and simulator jobs
continued; these observations are not an isolated or randomized timing study.

Deployment remains unapproved. A bounded representative-input pilot with explicit
runtime/resource limits and audited completed outputs is still needed before a
large restart; small synthetic graphs cannot establish its completion cost.
The one-thread fidelity queue keeps its original tool and the simulator remains
unchanged. No partial measurement or new candidate CDF enters the primary plots.

## Deployment gate

Do not clear the hold or launch another large twenty-thread TC merely because a
tiny case is faster. First require all correctness gates, repeated scaling,
a bounded larger-input test, a frozen candidate hash and explicit versioned
commands. Preserve unsuccessful lock alternatives. Rerun affected multithreaded
controls consistently as a new instrument-version control series, never silently
replace individual favorable workloads or mix versions into the primary figure.
The current validation script always records `deployment_approved: false`;
passing smoke tests is not automatic deployment approval.

## Real-input pilot declared on 1 November

After the one-thread queue finished, the user explicitly authorized the next
bounded real-input pilot. `experiments/validate_pin_real_input.py` prepares one
fixed nested induced subset of the completed TC Twitter input (SHA-256
`085d5efd0ebf4556d0a10d133017246bf0db4f0875063e92e28bb35efaa16f5a`).
It retains vertices whose SplitMix64 hash of the source CSR vertex ID is zero
modulo eight, preserving ascending order and all induced edges. These are already
relabelled IDs, not original Twitter IDs. The fraction is fixed before any pilot
timing or CDF and will not be enlarged or shrunk to obtain favorable results.
This is a reduced real-input proxy, not the full held graph or an M5 input.

The frozen baseline and candidate above are reused; only `local_bbl` is enabled
for the candidate. Both use the same executable, cold timed-kernel ROI, ten LLC
ways, one trial, and 1M modeled-event windows for finer engineering progress
reporting. No instruction-driven phase or cache-order relaxation is enabled.
Application triangle statistics are requested in both configurations.

The finite sequence is native one/twenty threads (120-second cap each), then
instrumented one-thread baseline/candidate, then twenty-thread baseline/candidate
and candidate/baseline. Each instrumented run has a 600-second deadline. A user
service adds a 75-minute overall cap, 3 GiB memory limit and 512 MiB swap limit;
it does not modify or stop Liblinear. Each case uses a fresh output directory.
RSS is sampled once/second across its process group (shared pages can double
count); timing includes wrapper startup and input hashing. ABBA reduces a simple
order bias but is not a randomized isolated-host timing study.

Completed cases must match native triangle counts and pass the existing paired
access/fill/traffic audits for pooled and whole scopes. The one-thread paired and
epoch CSVs must additionally match byte-for-byte. Concurrent traces need not be
identical. Timeouts preserve partial files and mark their manifests interrupted;
they cannot qualify as completed data or provide a complete-run speedup.
Failed cases and slower outcomes remain in the report. The report always keeps
`deployment_approved: false`: even a passing reduced proxy cannot establish the
cost of the much larger held TC input. No pilot CDF enters fidelity scoring or
the exploratory closest-case figure. The campaign's multithread hold is unchanged.

### Fixed follow-up for the capacity limitation

The first proxy's completed cases have no full 1M-event window: its serialized
graph is 20,709,073 bytes and the measured footprint is largely cache-resident.
This is useful for lock contention, but not a capacity-representative cost gate.
The one-thread paired/epoch CSVs were checked byte-for-byte; the overall pilot
must still finish before its timing result is published.

The next engineering check is declared before collection: use denominator four
instead of eight on exactly the same frozen source CSR, in a new output
directory. Retain all first-proxy outcomes. Keep the same tools, native checks,
one-thread exact-output gate, twenty-thread ABBA order, 600-second per-case
deadline and resource limits. Start only after the denominator-eight pilot
finishes with `passed bounded proxy` and its completed-output audits are
inspected. A failed exact-output check, wrong native answer or timeout blocks
the larger follow-up; publish that result without escalating cost. This larger subset is
motivated by the lack of full memory-event windows, not any reference CDF.
There is no automatic sequence of further graph resizing. If it times out or
still fails to exercise full windows, retain that negative result and leave
large deployment unapproved rather than extend the deadline after seeing it.
`--denominator 4` explicitly identifies this follow-up; the default remains eight.

### First real-input proxy completed

`real-input-attempt-1.json` under `results/pin-scalability-2026-10-31/` records
six completed, audited runs. Both native runs and all six instrumented runs
returned 957,682 triangles. The one-thread epoch and full paired CSVs match
byte-for-byte; an independent post-completion audit rechecked every case's
access/fill/traffic totals, histograms, populations and whole unions.

| Threads / case | Run 1 seconds | Run 2 seconds | Median seconds |
| --- | ---: | ---: | ---: |
| 1 / baseline | 29.203 | not repeated | 29.203 |
| 1 / local BBL | 22.418 | not repeated | 22.418 |
| 20 / baseline | 592.686 | 538.471 | 565.578 |
| 20 / local BBL | 287.469 | 275.048 | 281.259 |

The twenty-thread median instrument-runtime improvement is about 2.01x, yet
optimized twenty-thread profiling remains about 12.55x slower than optimized
one-thread profiling. Sampled process-group peak RSS is 257.5/258.0 MB for the
one-thread cases and 271.0--271.8 MB for the twenty-thread cases (decimal MB;
shared pages may double count). This is not an isolated-host application-speedup
measurement, and two repetitions do not establish a robust timing distribution.

Every run contains only its final partial event window: 284,441 memory events
at one thread and 284,671--284,672 at twenty threads, below 1M. The twenty-thread
access totals vary slightly (426,734,500--426,734,532); exact concurrent traces
are not claimed. This confirms why the smaller proxy cannot approve the full
held graph. The declared denominator-four capacity follow-up was launched only
after the first report passed and all six outputs were independently re-audited.
It retains the original fixed timeouts, all failures and the large-run hold.

### Capacity follow-up: runtime gate not passed

The denominator-four follow-up finished with `pilot not passed`. Its small
terminal report is archived as `real-input-capacity-attempt-1.json` in the same
results directory. The 62,903,561-byte graph has 2,602,852 vertices and 10,520,180
directed adjacency entries; SHA-256 is
`068e183fc38b871912cd07dc0bca512213d6d6db7c77a263991f3dfadf419556`.

| Threads / case | Run 1 seconds | Run 2 seconds | Completed and audited |
| --- | ---: | ---: | --- |
| 1 / baseline | 375.897 | not repeated | yes |
| 1 / local BBL | 290.720 | not repeated | yes |
| 20 / baseline | timeout at 600 | timeout at 600 | no |
| 20 / local BBL | timeout at 600 | timeout at 600 | no |

Both native runs and the completed one-thread instrumented runs returned
8,438,439 triangles. Their epoch/full paired CSVs match byte-for-byte. Independent
audits confirm 5,766,344,921 demand accesses, 890,779 fills and 890,814 modeled
memory events in each completed run. Even these completed runs do not contain
a full 1M-event window, so increasing serialized graph size did not establish
the required full-window memory-traffic behavior. File size alone is not the
modeled cache working set.

The four timeouts were checked to have interrupted manifests with the explicit
600-second reason. Their partial files remain only in external engineering
storage; no partial CDF is published. No pilot processes remain. The service
returned exit code 1 for the failed gate, not an OOM or an unhandled exception;
systemd reported a 448,159,744-byte peak, below the 3 GiB limit.

The one-thread instrument-runtime reduction is about 1.29x in this single pair.
Both twenty-thread configurations exceeded the budget, so there is **no measured
complete-run twenty-thread speedup for this larger input**. Equal timeout limits
do not imply equal completion times. The first proxy's 2.01x cannot be projected
onto the full held input. No correctness failure was found in completed cases,
but the declared cost/representativeness gate did not pass.

Decision: preserve the negative result and keep `deployment_approved: false`
and the campaign's multithread hold. Do not enlarge or shrink another proxy,
extend deadlines post hoc, or restart the oversized TC under these pilot
instructions. The three held controls remain explicitly incomplete. Further
performance redesign or a different cost budget needs a newly declared decision,
not a silent continuation of this failed gate. Liblinear and the existing BC
simulator queue continue unchanged; no application speedup is claimed.
