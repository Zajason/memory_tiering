# Drive the CXL bridge with a known access pattern and check the probe against
# analytic ground truth -- the same calibration idea used for the pintool.
#
#   PyTrafficGen --> XBar --> CXLBridge (probe here) --> MemCtrl(DDR4)
#
# createLinear with block_size=64 touches every 64B word of every page it covers,
# so mean_unique_words must come out at exactly 64.0. Anything else means the
# probe is not seeing the request stream it claims to see.

import argparse
import m5
from m5.objects import *

parser = argparse.ArgumentParser()
parser.add_argument('--duration-ticks', type=int, default=200000000)
parser.add_argument('--epoch-events', type=int, default=0)
parser.add_argument('--with-cache', action='store_true')
parser.add_argument('--read-percent', type=int, default=100)
args = parser.parse_args()
if args.duration_ticks <= 0 or args.epoch_events < 0:
    parser.error('duration must be positive and epoch size nonnegative')
if not 0 <= args.read_percent <= 100:
    parser.error('read percentage must be between 0 and 100')

system = System()
system.clk_domain = SrcClockDomain(clock="2GHz",
                                   voltage_domain=VoltageDomain())
system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MB")]

system.gen = PyTrafficGen()
system.xbar = NoncoherentXBar(width=16, frontend_latency=1,
                              forward_latency=1, response_latency=1)

system.cxl = CXLBridge(
    ranges=system.mem_ranges,
    hotskew_enable=True,
    hotskew_out="hotskew",
    hotskew_epoch=args.epoch_events,
    hotskew_topk=128,
    hotskew_budgets=[128, 512, 2048],
)

system.mem_ctrl = MemCtrl(hotskew_enable=True, hotskew_out='hotskew-controller',
                         hotskew_epoch=args.epoch_events, hotskew_budgets=[])
system.mem_ctrl.dram = DDR4_2400_8x8(range=system.mem_ranges[0])

system.gen.port = system.xbar.cpu_side_ports
system.system_port = system.xbar.cpu_side_ports
if args.with_cache:
    system.cache = Cache(size='32KiB', assoc=4, tag_latency=2,
                         data_latency=2, response_latency=2, mshrs=16,
                         tgts_per_mshr=8)
    system.membus = SystemXBar()
    system.xbar.mem_side_ports = system.cache.cpu_side
    system.cache.mem_side = system.membus.cpu_side_ports
    system.membus.mem_side_ports = system.cxl.cpu_side_port
else:
    system.xbar.mem_side_ports = system.cxl.cpu_side_port
system.cxl.mem_side_port = system.mem_ctrl.port

root = Root(full_system=False, system=system)
m5.instantiate()

SWEEP = 16 * 1024 * 1024          # 16 MB == 4096 pages
def trace():
    yield system.gen.createLinear(args.duration_ticks, 0, SWEEP, 64, 1000, 1000, args.read_percent, 0)
    yield system.gen.createExit(0)

system.gen.start(trace())
event = m5.simulate()
print("exiting @ tick", m5.curTick(), "because", event.getCause())
# Finish accepted requests before comparing the two request-path probes.
m5.drain()
print("drained @ tick", m5.curTick())
print("The timed generator may stop mid-page; verify events == sum(words * pages).")
