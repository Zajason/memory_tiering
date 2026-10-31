# Declared Pin stage 2 protocol: 28 October 2026

## 31 October operational amendment

The user authorized stopping the oversized twenty-thread TC attempt and improving
profiler scalability without weakening measurement reliability. That attempt is
`interrupted`, not complete; its files remain in `footprint20-tc/attempt-1` and
must never enter completed CDF comparisons. `campaign.json` now records
`multithread_hold: true`. Do not automatically restart or clear this hold.

The service continues only the remaining one-thread process-scope and nine-way
controls, using the frozen original tool hash. The simulator runs independently
and is not stopped or modified. Candidate instrumentation is built separately
and is not deployed merely because a timing test is faster. See
[Pin scalability validation](pin-scalability.md) for the validation and rollout gates.

The user requested all remaining justified controls, both access and miss plots,
retention of closer results, and presentation updates. All outcomes are retained.
Lower-error cases are preserved as exploratory controls, not silently substituted
for a common-protocol reproduction. Access and miss scores are both reported.

## Cases

- Full observed process, including observed setup, versus timed-kernel ROI.
  Kernel copies remain invisible to Pin. This does not reconstruct device traffic
  during setup. Whole-ROI and pooled page-window CDFs remain separate outputs.
- Twenty software threads on the declared real-input reductions, rather than
  only the earlier kron-23 thread control. This is not a coherent 20-core CPU model.
- Nine LLC ways / 36 MiB instead of ten / 40 MiB on the same inputs, one thread.
- Native-RSS-selected TC graph: induced original Twitter hash fractions
  11/16, 10/16, 12/16, in that order. Target 5,000,000,000 bytes peak RSS at
  20 native threads, tolerance 10%. Stop at the first matching candidate; if none
  match, select the nearest native RSS and explicitly report the residual gap.
  Paper GB/GiB ambiguity remains. No CDF or M5 curve is consulted during selection.
  Measure the selected graph under Pin at both one and twenty threads.

Other settings remain unchanged: stock GAPBS, one trial, cold initial model,
10M total modeled memory-event windows, final partial windows included, paired
access/fill/writeback-inclusive measurements. PR uses the benchmark default here;
the prior artifact-convergence control remains separately reported.

Shorter kernels BFS/CC/BC/SSSP precede footprint preparation and expensive PR/TC
controls. The service waits for the already-declared 200-trial repetition controls
to finish. It runs one instrumented workload at a time and preserves failed
attempts in new directories. It waits for 12 GiB available host memory before
starting a job; native footprint preparation additionally waits for 26 GiB.
Complete results enter the stage 2 report only after
population, event-total and histogram checks.

## Operation and reports

- Runner: `experiments/run_pin_fidelity_stage2.py`.
- Service: `memory-tiering-pin-fidelity-stage2`.
- State/results: `results/fidelity-stage2-2026-10-28/`.
- Publication: `src/analysis/publish_pin_stage2.py`.
- Report: [pin-fidelity-stage2.md](pin-fidelity-stage2.md).

Do not interpret exploratory closest-case selection as an independent replication
test. A preferred scientific protocol needs evidence beyond its closeness to M5.
Never replace only the unfavorable workloads or switch pooled/whole scope silently.

The existing checkpointed SimCXL queue continues independently, including PR and
TC. Existing graph results remain complete; active guest disks/configuration must
not be modified. Simulator results and their pending status belong in the same
presentation, with the differing inputs and request stream explicitly identified.

Pin stage 2 cannot resume mid-run after shutdown. To stop everything for Windows,
stop this service and the repetition service; pause the active simulator using
its checkpoint supervisor and wait for confirmed `paused` first.
