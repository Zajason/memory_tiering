# Fidelity work resumed: 28 October 2026

The user authorized continuing the paused measurements and investigating all
defensible routes toward the M5 distributions. This is not permission to optimize
parameters against the published bars. There is no finite proof that every
possible cause has been exhausted, nor evidence for a hardware-imposed ceiling.

## Running and queued

1. Resume the existing declared input campaign: Twitter PR/TC and Google+ BC/SSSP.
   Completed BFS/CC and all earlier execution controls are reused. Yesterday's
   incomplete PR output remains in place; the restarted PR uses `dataset/attempt-1`.
2. After that campaign, run the already-declared 200-trial BFS/CC repetition
   controls. They use kron-23 and one thread, not the authors' unavailable inputs.
3. After the input campaign, resume the remaining simulator jobs with periodic
   process snapshots: PR, TC, Liblinear, and BC 1M/100M-event window controls.
   Reuse complete BFS/CC/BC/SSSP. The bounded full-system restore proof passed
   with the matching gem5 hash; a real reboot test remains unproven.
4. Publish all outcomes, including worse agreement. Retain the distinct clocks,
   whole/pooled scopes, touched-page populations and accesses/fills/traffic.

The simulator comparison is now available in [simulator-figure4.md](simulator-figure4.md).
Its all-Kronecker traffic control is important: the primary Pin baseline uses
Google+ for BC/SSSP, while the current simulator uses kron-23. No CDF difference
between those configurations isolates a cache or kernel effect.

## Evidence to inspect before adding more runs

- Compare real-input outcomes against both the old input-family baseline and the
  declared whole-ROI distributions. Report all five thresholds, not a tail point.
- Keep native RSS versus file size explicit. The new TC native RSS is about
  0.71 GiB, whereas M5 Table 3 reports a 5.0 GB footprint. The artifact's separately
  reduced TC filename does not establish the same working set. Other new input
  footprints also differ. Do not claim that downloading Twitter reproduces size.
- Separate single-factor tests from interactions: the current 20-thread control
  uses kron-23 and the real-input campaign uses one thread. Their combination has
  not been measured. A later joint control must be labelled as such, costed, and
  declared before collection rather than selected from promising curves.
- The paper table states 10 LLC ways; the public artifact mask enables nine.
  A nine-way control is justified by that discrepancy, not by an observed fit.
- Static guest binaries, a different kernel and TimingSimpleCPU are not the same
  execution as native dynamically linked GAPBS under Pin. A same-graph-family
  comparison helps but is not full input/binary equivalence.

## External gaps and limits

M5 describes two possible region collection strategies and 128 MiB WAC regions,
but does not resolve the exact Figure 4 reset/region schedule in the evidence we
have recovered. Figure 3's ten random execution points and a Figure 8 manager
polling cadence must not be assigned to Figure 4. The stale claim doing that in
`papers/README.md` has now been corrected.

The exact reduced graphs, ordering, weights and Figure 4 page denominator remain
unavailable. The [author clarification request](m5-author-request.md) is a draft,
not a sent message. Physical placement, prefetching, coherent multicore effects
and instruction traffic are further differences, not proven explanations.

Reference: [M5 paper, sections 3, 4.1 and 6](https://jiyuan.is/papers/asplos25-m5.pdf).
