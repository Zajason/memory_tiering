# fs_hotskew.py -- full-system gem5 run of the hot-skewness probe.
#
#   ./build/X86/gem5.opt fs_hotskew.py --workload sssp|bc|liblinear
#
# What this measures, and why it is not the same instrument as the pintool
# -----------------------------------------------------------------------
# The probe sits in MemCtrl::recvTimingReq -- post-LLC, so the stream it sees is
# the same quantity the pintool calls "dram_accesses" (LLC misses + writebacks).
# Two things differ, and they are the entire reason for running here:
#
#   * addresses are PHYSICAL, so page-keyed trackers are not layout-dependent;
#   * KERNEL traffic is included -- read(2), page-fault zeroing, DMA. Pin cannot
#     see any of it (docs/report.md Sec 4.2), and that blind spot is the leading
#     explanation for where we disagree with M5.
#
# Cache hierarchy is set to match configs/spr-20t.env: 48kB/12-way L1d,
# 2MB/16-way L2, 36MB/9-way L3. One core, because the Pin headline runs are
# single-threaded (docs/methodology.md, "Why the headline runs are single-threaded").
#
# Why the probe is at the memory controller and not the CXL bridge
# ---------------------------------------------------------------
# The CXL-bridge integration exists and is verified (0001-hotskew-probe.patch),
# but SimCXL exposes CXL memory as E820 type 20, which Linux treats as reserved
# unless the CXL driver claims it. That needs SimCXL's custom 6.12 kernel; the
# stock gem5 kernel would route nothing through the bridge and the probe would
# silently report an empty run. The memory controller carries the traffic under
# any kernel, and for a distribution over addresses the placement is equivalent.
#
# Flow
# ----
#   1. boot under KVM (near-native speed)
#   2. the boot script m5-exits; we switch to TimingSimpleCPU
#   3. the workload runs in detail, INCLUDING its data load -- that is
#      deliberate. The user-space-load experiment showed load visibility is
#      worth 26.7 of the 28.6 words/page difference, so excluding it would
#      reproduce the pintool's blind spot in a simulator that does not have one.
#   4. the binaries' hotskew_roi_begin/end markers m5-exit too; those are
#      recorded as epoch boundaries, not used to gate the measurement.
#   5. we stop at --max-epochs and write the summary.

import argparse
import m5
from m5.objects import Root
from gem5.utils.requires import requires
from gem5.components.boards.x86_board import X86Board
from gem5.components.memory.single_channel import SingleChannelDDR4_3200
from gem5.components.processors.simple_switchable_processor import (
    SimpleSwitchableProcessor,
)
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.cachehierarchies.classic.private_l1_private_l2_shared_l3_cache_hierarchy import (
    PrivateL1PrivateL2SharedL3CacheHierarchy,
)
from gem5.isas import ISA
from gem5.simulate.simulator import Simulator
from gem5.simulate.exit_event import ExitEvent
from gem5.resources.resource import DiskImageResource, KernelResource

from m5.objects import CowDiskImage, IdeDisk, RawDiskImage

requires(isa_required=ISA.X86)


def _make_disk(path, drive_id):
    """An IDE disk backed by a copy-on-write overlay.

    Copy-on-write so a crashed or killed run cannot corrupt the images we built;
    retrying then costs nothing.
    """
    disk = IdeDisk()
    disk.driveID = drive_id
    disk.image = CowDiskImage(
        child=RawDiskImage(read_only=True), read_only=False
    )
    disk.image.child.image_file = path
    return disk


class TwoDiskX86Board(X86Board):
    """X86Board that attaches a second disk holding the benchmark data.

    The data (kron-23.wsg 2.0 GB, kron-23.sg 1.1 GB, kdda 2.67 GB) does not fit
    in the 2 GB stock Ubuntu image, and rebuilding that image needs root. A
    second disk built with `mkfs.ext4 -d` needs none.

    This has to be done by overriding the board's own hook rather than by
    assigning to `pc.south_bridge.ide.disks` after construction: a SimObject
    created outside the board's lifecycle is never parented into the tree, and
    m5.instantiate() fails with "Attempt to instantiate orphan node".
    """

    def __init__(self, *a, data_image=None, **kw):
        self._data_image = data_image
        super().__init__(*a, **kw)

    def get_disk_device(self):
        # This kernel binds the IDE disks through ide-gd, so they enumerate as
        # /dev/hdX. X86Board's default of /dev/sda1 makes the kernel panic with
        # "VFS: Unable to mount root fs on unknown-block(0,0)".
        return "/dev/hda1"

    def _add_disk_to_board(self, disk_image):
        disks = [_make_disk(disk_image.get_local_path(), "device0")]
        if self._data_image:
            disks.append(_make_disk(self._data_image, "device1"))
        self.pc.south_bridge.ide.disks = disks

ap = argparse.ArgumentParser()
ap.add_argument("--workload", required=True, choices=["sssp", "bc", "liblinear"])
ap.add_argument("--fs-dir", default="/home/zajason/dev/advarch/fs_image")
ap.add_argument("--epoch", type=int, default=10_000_000)
ap.add_argument("--max-epochs", type=int, default=12)
ap.add_argument("--max-exits", type=int, default=4,
                help="stop on this m5_exit; 4 = boot + roi_begin + roi_end + script end")
ap.add_argument("--outfile", default=None)
args = ap.parse_args()

# Matches configs/spr-20t.env -- M5's GAPBS CAT partition.
cache_hierarchy = PrivateL1PrivateL2SharedL3CacheHierarchy(
    l1d_size="48kB", l1d_assoc=12,
    l1i_size="32kB", l1i_assoc=8,
    l2_size="2MB",   l2_assoc=16,
    l3_size="36MB",  l3_assoc=9,
)

# 3 GB is the ceiling X86Board allows (I/O hole at 0xC0000000). Measured peak
# RSS on the host: bc 1.26 GB, sssp 2.19 GB -- both fit. liblinear peaks at
# 11.94 GB and does NOT; see README.md.
memory = SingleChannelDDR4_3200(size="3GB")

processor = SimpleSwitchableProcessor(
    starting_core_type=CPUTypes.ATOMIC,
    switch_core_type=CPUTypes.TIMING,
    isa=ISA.X86,
    num_cores=1,
)
for proc in []:  # usePerf only applies to KVM
    proc.core.usePerf = False

board = TwoDiskX86Board(
    clk_freq="3GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
    cxl_memory=SingleChannelDDR4_3200(size="1GB"),
    is_asic=True,
    data_image=f"{args.fs_dir}/data.img",
)

# Enable the probe on every memory controller behind this board's memory.
out = args.outfile or f"hotskew-{args.workload}"
n_enabled = 0
for ctrl in memory.get_memory_controllers():
    ctrl.hotskew_enable = True
    ctrl.hotskew_out = out
    ctrl.hotskew_epoch = args.epoch
    ctrl.hotskew_topk = 128
    ctrl.hotskew_budgets = [128, 512, 2048, 8192]
    n_enabled += 1
print(f"hotskew: probe enabled on {n_enabled} memory controller(s) -> {out}")

command = (
    "m5 exit;"                       # hand back so we can switch to the detailed CPU
    + "mkdir -p /data;"
    # data.img is a bare ext4 filesystem with no partition table, so it is
    # /dev/hdb, not /dev/hdb1 -- and hd, not sd, because of ide-gd (above).
    + "mount /dev/hdb /data;"
    + f"/data/run_{args.workload}.sh;"
    + "m5 exit;"
)

board.set_kernel_disk_workload(
    kernel=KernelResource(local_path=f"{args.fs_dir}/vmlinux-5.4.49"),
    disk_image=DiskImageResource(local_path=f"{args.fs_dir}/x86-ubuntu.img"),
    readfile_contents=command,
    kernel_args=board.get_default_kernel_args() + ["idle=nomwait"],
)

print(f"hotskew: {len(board.pc.south_bridge.ide.disks)} disks attached")


class Phase:
    switched = False
    exits = 0


def on_exit():
    """Every m5_exit lands here, in order:

      #1  the boot script's handback  -> switch ATOMIC -> TimingSimpleCPU
      #2  hotskew_roi_begin()         -> the binary entering its timed kernel
      #3  hotskew_roi_end()           -> leaving it
      #4  the boot script's final exit -> workload done, stop

    The ROI markers are recorded but do NOT gate the measurement: the probe
    counts from the CPU switch onward, so the data load is included. That is
    deliberate (see the header).

    Stopping on #4 matters. Without it the guest sits at an idle shell forever
    and the run never writes a summary.
    """
    while True:
        Phase.exits += 1
        if not Phase.switched:
            print(f"hotskew: boot done at tick {m5.curTick()}, "
                  f"switching to TimingSimpleCPU", flush=True)
            processor.switch()
            Phase.switched = True
            yield False
        elif Phase.exits >= args.max_exits:
            print(f"hotskew: exit #{Phase.exits} at tick {m5.curTick()} "
                  f"-- stopping, summary follows", flush=True)
            yield True
        else:
            print(f"hotskew: ROI marker (exit #{Phase.exits}) at "
                  f"tick {m5.curTick()}", flush=True)
            yield False


simulator = Simulator(
    board=board,
    on_exit_event={ExitEvent.EXIT: on_exit()},
)
simulator.run()
print("hotskew: run complete; summary written by the exit callback")
