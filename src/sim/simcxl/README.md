# Running the probe inside a CXL simulator

`src/sim/hotskew_probe.hpp` was written to be hooked into a simulator by one call per
memory request. This directory is that hook, actually applied and actually run.

## Why this matters more than it looks

The Pin-based profiler has two limits that no amount of care removes, because they are
properties of where it sits (`docs/report.md` §4.2):

* it sees **virtual** addresses, so anything keyed on page number is layout-dependent;
* it is **blind to kernel traffic** — `read(2)`, page-fault zeroing, DMA. Isolating
  that was the single largest correction in this project: BFS P(≤48) moved from
  **0.813 to 0.320** against M5's published **0.345** once the graph load was done in
  user space instead of by the kernel.

Inside the simulator both limits disappear. The probe sits on the CXL device's request
path, where addresses are physical and every requestor is visible. Nothing in the
counting code changes — that was the design claim, and it held.

## Target

**SimCXL / CXL-DMSim** — https://github.com/ferry-hhh/CXL-DMSim — gem5 23.1,
full-system, cycle-level, CXL.io/.cache/.mem, Type 1/2/3 devices.

Not CXLRAMSim: that one is still unreleased (its paper says "we plan to open-source").
The CXLRAMSim authors criticise CXL-DMSim for attaching CXL to the MemBus rather than
the IOBus. That critique is about **timing** fidelity and does not affect *which
addresses reach the device*, which is the only property this measurement depends on.
If CXLRAMSim is released, the same patch moves across.

## Build (verified on this machine, 2026-09-18)

Ubuntu 26.04, gcc 15.2, Python 3.14.4 — all **newer** than upstream asks for, and all
fine. gem5's only gates are gcc ≥ 7 and Python ≥ 3.6.

```bash
git clone https://github.com/ferry-hhh/CXL-DMSim.git simcxl
sudo apt-get install -y zlib1g-dev libprotobuf-dev protobuf-compiler \
     libgoogle-perftools-dev libboost-serialization-dev libboost-iostreams-dev \
     libpng-dev libelf-dev m4
python3 -m venv venv && ./venv/bin/pip install 'scons==4.5.2'
cd simcxl && ../venv/bin/scons build/X86/gem5.opt -j"$(nproc)" --ignore-style
```

Two traps, both of which cost time here:

* **Pin SCons to 4.5.2.** `pip install scons` currently gives 4.11.1b, whose
  `CheckLibWithHeader` fails to link `-lz` inside gem5's environment and reports
  *"Did not find needed zlib compression library"* while `g++ -lz` works by hand. The
  error names the wrong component entirely.
* **`--config=force`** if you install a dependency after a failed configure; gem5
  caches configure results and will keep reporting the old failure.

`gcc-12` is *not* required, despite the upstream README. gcc-15 builds it clean.

## Apply the probe

```bash
cd simcxl
mkdir -p src/mem/hotskew
cp ../memory_tiering/src/profiler/pintool/counter_table.hpp src/mem/hotskew/
cp ../memory_tiering/src/profiler/pintool/tracker.hpp       src/mem/hotskew/
cp ../memory_tiering/src/sim/hotskew_probe.hpp              src/mem/hotskew/
sed -i 's#\.\./profiler/pintool/#./#g' src/mem/hotskew/hotskew_probe.hpp
git apply ../memory_tiering/src/sim/simcxl/0001-hotskew-probe.patch
../venv/bin/scons build/X86/gem5.opt -j"$(nproc)" --ignore-style
```

The patch adds six parameters to the `CXLBridge` SimObject and one call in
`BridgeResponsePort::recvTimingReq`:

| parameter | default | meaning |
|---|---|---|
| `hotskew_enable` | `False` | profile this bridge |
| `hotskew_out` | `"hotskew"` | output file, relative to the gem5 output dir |
| `hotskew_epoch` | `10000000` | close an epoch every N requests; `0` = at exit only |
| `hotskew_topk` | `128` | hot pages the tracker reports |
| `hotskew_budgets` | `[128,512,2048,8192]` | tracker sizes evaluated **concurrently** |
| `hotskew_countmin` | `False` | Count-Min (NeoMem) instead of Space-Saving |

## Verify

```bash
./build/X86/gem5.opt ../memory_tiering/src/sim/simcxl/cxl_hotskew_test.py
cat m5out/hotskew
```

A traffic generator sweeps 64 B blocks linearly through the bridge, so every word of
every page it reaches is touched exactly once and the answer is known in advance —
the same analytic-ground-truth approach used to calibrate the pintool. Expected
(`expected_linear_sweep.txt`):

```
page_observations  474
dram_accesses      30321
mean_unique_words  63.968 / 64
```

`63.968` rather than a flat `64.000` is correct, not slop: the run ends mid-page, so
473 complete pages plus 49 words of a 474th give 30 321 accesses, and
30 321 / 474 = 63.968. **Accesses equal unique lines** — that identity is what the
check is really for.

### The bug that identity caught

The obvious place for the hook is the top of `recvTimingReq`. It is wrong. A request
that arrives when the queue is full is rejected with `false` and **re-sent** by the
requestor, so counting on entry counts it once per retry. The first run reported
**87 558** accesses instead of 30 321 — inflated 2.89× — while the page set stayed
correct and `mean_unique_words` stayed at 63.968.

That is the dangerous shape of error: every number that gets quoted still looks
reasonable, and only an independent identity exposes it. The call now sits inside the
`if (!retryReq)` block, where the request is actually accepted.

## What is not done

Running a **real workload** needs full-system mode: an x86 kernel and a disk image
(`configs/example/gem5_library/x86-cxl-type3-with-classic.py` expects `vmlinux` and a
`parsec.img`, several GB, at paths hardcoded to the upstream author's home directory).
Nothing blocks it except fetching those images and the simulation time — full-system
gem5 on a GAPBS-sized input is hours to days, against about 40 minutes under Pin.

So this is the instrument, demonstrated correct on synthetic traffic, not a
replacement set of results. The honest framing: **the port is done and verified; the
campaign is not run.**
