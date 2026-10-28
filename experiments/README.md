# Experiments

The current goal is the M5 Figure 4 characterization: distinct 64-byte lines per
4 KiB page, measured from application accesses and modeled memory traffic.
The exact authors' inputs and Figure 4 collection procedure remain unresolved.

## Current runners

| Runner | Purpose |
|---|---|
| `run_paired.py` | Paired access/fill/traffic measurements with manifests and explicit thread/trial/window controls |
| `run_fidelity_campaign.py` | Predeclared input and execution controls; updates the fidelity report after each completion |
| `run_pin_fidelity_stage2.py` | Paired process-scope, real-input/thread, nine-way and native-RSS-selected TC controls |
| `revalidation_campaign.py` | Corrected tracker/extension runs and full-system simulator queue |
| `run_extension_workload.py` | Redis A/C, Memcached and Liblinear with compressed raw records |
| `test_process_checkpoint.py` | Kill/restore versus uninterrupted synthetic or bounded full-system run |
| `checkpoint_sim.py` | Periodic snapshots and explicit pause/resume for a simulator process |
| `resume_sim_after_fidelity.py` | Waits for completed dataset campaign, then executes the validated checkpointed simulator queue |
| `migrate_raw_storage.py` | SHA256-verified migration of ignored raw records to the research HDD |

See [current measurement semantics](../docs/methodology.md),
[27 October fidelity controls](../docs/fidelity-followup.md), and
[corrected extension results](../docs/revalidation-2026-10-25.md).

## Fidelity campaign

```bash
.venv/bin/python experiments/run_fidelity_campaign.py
```

This runs the declared controls in sequence. Completed jobs with compatible
profiler hashes are reused; incomplete benchmark attempts use new directories.
The raw Twitter chunks must first be fetched with `benchmarks/fetch_twitter.py`.
Large files live under `/mnt/research/memory-tiering`; the reduced input rules and
hashes are recorded in the campaign's `inputs.json`. Reductions are our own
documented input-family experiments. They are not the missing M5 input files.

Twenty-thread runs have per-thread private caches and a serialized shared LLC;
the Pin model does not simulate coherence. Three-trial controls assess scope and
repetition, while the artifact's performance commands use many more trials.
Do not silently treat performance-script settings as Figure 4's collection scope.

Stage 2 is declared in [its protocol](../docs/pin-stage2-protocol.md), runs as
`memory-tiering-pin-fidelity-stage2`, and waits for the repetition controls.
`run_paired.py --scope process` removes ROI gating without changing the
instrument; `--scope kernel` remains the default. The process mode still cannot
observe kernel execution. `test_paired_scope.py` exercises both modes on a tiny
actual Pin run. Native footprint preparation waits for 26 GiB available RAM.

## Simulator pause and resume

```bash
.venv/bin/python experiments/checkpoint_sim.py pause --state-dir DIRECTORY
```

Wait for confirmed `paused` before shutdown. The supervisor's run command restores
its last complete snapshot; the same binary, command, configuration and guarded
input files must be available. A normal kill can lose progress since the last
periodic checkpoint. The simulator queue accepts `--checkpoint-storage DIRECTORY`
and `--checkpoint-validation REPORT.json`, refusing a missing or incompatible
full-system restore validation. See [checkpointing](../docs/checkpointing.md).

The resumed `memory-tiering-revalidate-sim` service initially runs
`resume_sim_after_fidelity.py`, waiting without running gem5. Once the input
campaign completes, it executes the checkpointed lane in the same service.
An interrupted or failed input campaign stops this waiter instead of starting
simulations. Stop the waiting service too when pausing all work. While gem5 is
running, use the explicit checkpoint pause command before stopping the service.

Generate the Figure 4-style device-side comparison from complete simulator jobs:

```bash
.venv/bin/python src/analysis/compare_simulator_m5.py
```

This reports each port independently, verifies completion and full histograms,
and marks missing workloads as pending. The main overview retains the current
Pin baseline; a supplementary all-kron-23 total-traffic control reduces the
input-family and read/write stream mismatches without claiming identical traces.

Full-system runs use SimCXL/CXL-DMSim, kernel and disk images already available on
the workstation. They can expose 19 GiB of guest RAM. CXLRAMSim access remains a
separate question; it is not a prerequisite for the current SimCXL measurements.

## Data and provenance

Preserve complete commands, input/executable/profiler hashes, workload parameters,
scope and completion state. Include partial final windows as declared. A growing
summary is not evidence of completed execution and is not a resumable checkpoint.
Report accesses, demand fills and writeback-inclusive traffic separately.
Serial memory-cost estimates do not establish application speedup.
