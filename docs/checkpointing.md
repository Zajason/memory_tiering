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

This is NOT yet full-system certification, a reboot test, or proof that arbitrary
workloads can resume. The full campaign remains stopped and its automatic monitor
remains paused. These tests establish process restore feasibility on this machine.

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
4. Add explicit checkpoint-complete, paused and resume states to the campaign
   runner. Do not let a checkpoint-and-kill operation become a failed benchmark
   or cause the next queued benchmark to start.
5. Budget disk space for an old valid snapshot plus its replacement, preserving
   the old snapshot until the new one is complete. Full-system compression is
   not measured yet. Only about 4.6 GiB was free during feasibility testing;
   this is insufficient headroom for the previous 10+ GiB simulator process.

Completed campaign results are safe. The interrupted PageRank attempt has no
checkpoint and cannot be recovered by adding this feature retroactively.

Reference: [DMTCP quick start](https://dmtcp.github.io/quick-start.html).
