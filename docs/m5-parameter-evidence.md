# M5 parameter evidence: renewed search, 28 October 2026

This is a source audit, not a newly chosen measurement protocol. Existing runs
continue unchanged. No author email has been sent.

## Confirmed settings versus missing Figure 4 settings

| Evidence | Confirmed | Not established by it |
|---|---|---|
| Paper sections 3 and 4.1 | 4 KiB pages, 64 B words, five thresholds; WAC observes device-side requests | Exact collection start/end and page denominator |
| Paper section 3 | WAC covers a 128 MB region using 4-bit counters; two collection strategies are described | Which strategy, region order, reset interval and aggregation generated Figure 4 |
| Paper Table 3 | Graph workloads: 20 cores / 10 ways; TC footprint 5.0 GB, other graph kernels 6.9 GB | Exact reduced inputs and compiler/source revision for the characterization |
| Artifact CAT script | Mask `0x7FC0`, nine set bits; benchmark cores 0–19 | Whether Figure 4 follows this script or the table |
| Performance command scripts | BFS/CC n200; BC n100; SSSP n200; PR n20 with i1000/t1e-4; TC n1 | Whether Figure 4 uses these performance invocations |

Sources: [paper](https://jiyuan.is/papers/asplos25-m5.pdf),
[CAT script](https://github.com/ece-fast-lab/ASPLOS-2025-M5/blob/main/setup/core_pqos/set_20t_llc.sh),
[benchmark commands](https://github.com/ece-fast-lab/ASPLOS-2025-M5/tree/main/testing_scripts/20_threads/bench_cmds).

The Figure 3 ten-point sampling and Figure 8 manager cadence are not recovered
Figure 4 parameters. The public scripts have workload-dependent manager settings;
there is no justification for assigning one of these to our CDF by default.

## Additional sources inspected

- [Zenodo latest archive](https://zenodo.org/records/14303160):
  `m5_zenodo_v3.zip`, 105,712,054 bytes, verified published MD5
  `5747fffed8bb3ea4b7d58208014fc827`; 3,699 ZIP entries. Benchmark scripts and
  Figure 8/9/10 processing are present. No Figure 4 runner or exact graph inputs
  were located by entry-name and targeted script inspection.
- [Earlier archive](https://zenodo.org/records/14232671):
  `m5_zenodo_v1.zip`, 368,446,607 bytes, verified published MD5
  `ab1423548855f5c3eb7deacc1dcb7f48`; 95,060 ZIP entries, largely the included
  kernel tree. No Figure 4 procedure or graph reduction was recovered in the
  targeted non-kernel software/script search. A negative search is not proof that
  every line in an archive has been ruled out.
- [Oldest archive](https://zenodo.org/records/14165842):
  `m5_zenodo_v0.zip`, 74,440,741 bytes, published MD5 verified as
  `ef67a50d86cc6e84af8d8fa26bfb70f8`; 2,650 entries. No graph files with
  `.sg/.wsg/.wel/.el` extensions or matching Figure 4/WAC/sparsity script text
  were found in the targeted inspection.
- The [first author's slides](https://ynnsau.github.io/assets/slides/m5.pptx),
  linked from his website: inspected slide text and speaker-note XML. They confirm
  device-side profiling and independent trackers but do not supply the missing
  Figure 4 clock. There are no embedded chart/workbook parts from which to recover
  exact Figure 4 values.
- [Google+ source format](https://people.duke.edu/~zg70/gplus.html): the third
  column is first-seen TimeID, not distance. The artifact uses `.wel` inputs but
  does not publish their weight construction. Treating TimeID as distance merely
  because the filename is weighted would be an unsupported reconstruction.
- [CXL-Tracer from the same lab](https://github.com/ece-fast-lab/cxl-tracer)
  provides a physical tracing framework, not a recovered M5 trace dataset. It
  needs FPGA/CXL hardware and a collection machine; installing it on this PC
  would not supply those capabilities. Requesting recorded traces is an
  alternative to requesting the original reduced inputs and WAC dumps.

All three archive downloads finished and their published checksums matched.
Downloaded reference files stay on the research HDD, not in git.

## Best remaining tests, in order

1. **Resolve collection scope.** Publish pooled and whole-ROI curves side by side
   and test explicitly declared full-application versus timed-kernel collection.
   For the simulator, its default switch at guest exit 1 includes graph loading;
   `--switch-at-roi` switches at exit 2 and excludes it. Pin cannot see kernel
   copies, so a user-space staging copy is not a substitute for the full-system
   test. Neither result should be picked as the answer after seeing agreement.
2. **Match workload footprint independently of the curve.** TC's native RSS is
   about 0.71 GiB, not the paper's 5.0 GB. Select future reductions using native
   RSS and graph properties before profiling, keeping vertex-order and selection
   rules explicit. Size matching alone cannot recover an unknown graph.
3. **Test execution interactions.** Combine the documented real-input family with
   20 threads; current controls test these factors separately. Then assess the
   artifact's nine-way LLC configuration as a separate control. The software
   model still lacks real multicore coherence and prefetching.
4. **Strengthen the simulator comparison.** Use identical graph hashes and
   comparable benchmark builds across Pin and the guest, then compare collection
   scopes. Current all-Kronecker comparisons match a family, not proven identical
   binaries/traces. Preserve existing checkpoints and guarded disk images; do not
   alter the guest image while the current simulator is using it.
5. **Seek original evidence.** Exact graph reductions, WAC snapshots or traces and
   region/reset instructions would constrain these choices more directly than
   further free parameter sweeps. The author request remains a draft.

Four-bit saturation alone does not explain a touched-line CDF: once a line's count
is nonzero, further increments do not change coverage. Counter wrap/reset behavior
would need actual evidence before using it as an explanation.
