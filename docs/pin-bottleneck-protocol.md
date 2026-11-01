# Bounded profiler bottleneck study

Declared on 1 November 2026 after the user explicitly requested a separate,
bounded engineering effort to identify the remaining bottleneck before redesign.
This is not another attempt to make an M5 curve closer. The large-run hold stays
active and no scientific collection settings, cache semantics or inputs change.

## Fixed scope

- Reuse the already prepared denominator-eight Twitter subset, SHA-256
  `76c74f519c81ca04c22bdc41ae30a9c5cad0d55b257f1cc60d395c9154151e41`.
  Do not create, resize or select another input.
- Reuse the frozen original and local-BBL candidate from `pin-scalability.md`.
  Do not rebuild either instrument or alter the measurement hot path.
- Profile six cases: one-thread baseline/candidate, then twenty-thread
  baseline/candidate and candidate/baseline. Same one-trial timed-kernel scope,
  cold caches, ten LLC ways and 1M-event diagnostic windows as the first proxy.
- Use external Linux perf user CPU-clock sampling at 99 Hz, with frame-pointer
  callchains. Each profile has a 40-second ceiling plus at most five seconds of
  shutdown grace; perf reporting has a 30-second ceiling. Six cases only.
- Run in a systemd user service with repository WorkingDirectory, Nice=10,
  2 GiB memory, 512 MiB swap and a ten-minute overall deadline. Liblinear remains
  untouched. A failed profiling permission or unsupported trace is reported,
  not bypassed through privilege escalation or repeated tool/settings changes.

## Questions and evidence

Measure sampled CPU proportions in synchronization symbols, the memory callback,
instruction callback, observer/epoch functions, other tool-linked code and other
runtime/application code. Keep unresolved/JIT samples in their own category; do
not discard them to inflate attribution. Keep leaf and callgraph evidence for
inspection; inlined cache/observer/lock operations may share a callback symbol.
If that ambiguity prevents a conclusion, state it rather than invent a split.

Sampled group RSS/CPU is contextual accounting, not an exact wall-time breakdown.
CPU-clock proportions describe user CPU consumption, not blocked wall time,
lock acquisition latency, memory stalls, or hardware cache misses. Fingerprints,
commands, perf version, kernel and CPU affinity are recorded. Different bounded
prefixes execute different amounts of work; their durations are not speedups.
Sampling perturbs timing, and the host is not isolated from the simulator.

Completed targets must retain native triangle counts and pass existing paired
audits. One-thread exact-output comparisons are retained when both complete.
Cutoff targets stay interrupted and cannot be published as complete experiments.
Raw perf data, logs and partial measurement files remain in external engineering
storage. Only terminal small attribution reports and the conservative assessment
are committed. No pilot CDF enters fidelity scoring or presentation comparison
plots. No automatic tool redesign, new graph, repeated budget expansion, large
restart or change to `deployment_approved: false` follows from this study.
