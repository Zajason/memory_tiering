# Checkpointing: feasibility and remaining validation

## Why native checkpoints are not enough here

The local gem5 classic-cache implementation does not serialize cache contents.
Our custom probe also lacks a native serializer for its current epoch, page/word
counters, histograms and bounded trackers. A native restore therefore cannot be
assumed to continue the same miss measurement. Flushing caches to make a native
checkpoint changes the measured stream.

We are testing DMTCP process snapshots instead: capture the simulator process,
including the caches, Python control flow, event queues and probe objects in its
address space. This is separate from gem5's architectural checkpoint mechanism.

## Current evidence

`results/checkpoint-tests/2026-10-26-synthetic-4/validation.json` records a passed
test: checkpoint during synthetic CXL traffic, kill the original process, restore
the saved process, finish, and compare against a fresh uninterrupted native run.
Both complete probe summaries were byte-identical, including tracker scores.
The compressed checkpoint was 36,641,618 bytes.

The mixed read/write cache test also passed:
`results/checkpoint-tests/2026-10-26-cached-2/validation.json`. Both complete probe
summaries match byte-for-byte; native and restored runs both finish draining at
tick 50,000,438,234. The compressed snapshot is 37,110,211 bytes.

The process supervisor has also passed two complete pause/restore cycles in one
cached synthetic run, preserving byte-identical probe summaries and completion
tick 50,000,438,234. The evidence is copied to
`results/fidelity-2026-10-27/checkpoint-manager-validation.json`.

Full-system validation is now running a bounded 64 MiB guest `dd` workload. It
waits until TimingSimpleCPU is active before checkpointing, then kills/restores
the process and compares against an uninterrupted run. Its report lives at
`/mnt/research/memory-tiering/checkpoint-validation/full-system-1/validation.json`.
This validation must pass before the long simulator queue uses the supervisor.
A reboot test and general certification across arbitrary workloads remain open.

## Local installation

DMTCP v4.2.0, commit `f8009ce7b4ad211311ca2f72a929b975e4aa1155`, is checked out
alongside the repository in `../dmtcp`, installed under `../dmtcp-local`.
No sudo or system installation was needed.

```bash
cd ../dmtcp
./configure --prefix="$HOME/dev/advarch/dmtcp-local" --enable-realtime-ckpt-signal
make -j4
make install
```

Two integration hazards were observed and handled in the test harness:

- gem5 uses SIGUSR2, DMTCP's default checkpoint signal. Build DMTCP with the
  realtime checkpoint signal option. The environment override alone did not
  avoid the conflict in our first attempts.
- This build's coordinator logged the blocking checkpoint command as unhandled.
  Do not assume command return means a snapshot is ready. The harness requests
  a checkpoint, waits for a finalized image and `RUNNING=yes`, then kills the
  original computation. A missing checkpoint is a failed test, not a saved run.

## Reproduce the test

Use a new output directory for every attempt:

```bash
.venv/bin/python experiments/test_process_checkpoint.py \
  --out results/checkpoint-tests/my-synthetic-test
.venv/bin/python experiments/test_process_checkpoint.py --with-cache \
  --out results/checkpoint-tests/my-cache-test
```

The cache variant uses a 32 KiB four-way cache, a coherent memory bus, and 50%
reads / 50% writes. The coherent bus consumes cache-maintenance traffic rather
than incorrectly forwarding it directly to DRAM. The original calibration's
defaults remain unchanged. Both tests use multiple probe epochs.

## Before restarting the long campaign

1. Validate full-system kill/restore with CPU, disks and in-flight memory traffic.
2. Compare uninterrupted and resumed final counts, histograms, tracker results
   and simulated completion tick. Check output-file handling across restore.
3. Test a real Linux reboot with unchanged binaries, libraries and input files.
   Never mount or modify the Linux filesystem from Windows while relying on a
   snapshot whose open files refer to it.
4. The runner now has explicit paused/resume handling: exit 75 preserves the
   current job and stops the lane. It checks the full-system validation report
   and matching gem5 binary hash before enabling checkpoints.
5. The research HDD now provides ample space. The supervisor requires 25 GiB
   free before making a snapshot, keeps the old valid snapshot during replacement,
   verifies checkpoint hashes on restore, and retains recent history. Full-system
   checkpoint size and time are still being measured.

## Operator commands

```bash
# Start or restore a managed process; same command and guarded files required.
.venv/bin/python experiments/checkpoint_sim.py run \
  --state-dir /mnt/research/memory-tiering/checkpoints/example -- gem5.opt CONFIG.py

# Wait for a finalized disk snapshot and confirmed paused state before shutdown.
.venv/bin/python experiments/checkpoint_sim.py pause \
  --state-dir /mnt/research/memory-tiering/checkpoints/example
```

The real simulator lane accepts `--checkpoint-storage DIRECTORY` and
`--checkpoint-validation REPORT.json`; it refuses synthetic-only or mismatched
validation reports. Routine process termination is not a substitute for the
explicit pause command. An unexpected stop can resume from the last completed
periodic snapshot, losing work since that snapshot. Snapshots use the same Linux
environment and unchanged guarded inputs; do not update these during a paused run.

Completed campaign results are safe. The interrupted PageRank attempt has no
checkpoint and cannot be recovered by adding this feature retroactively.

Reference: [DMTCP quick start](https://dmtcp.github.io/quick-start.html).
