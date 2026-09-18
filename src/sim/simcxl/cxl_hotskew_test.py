# Drive the CXL bridge with a known access pattern and check the probe against
# analytic ground truth -- the same calibration idea used for the pintool.
#
#   PyTrafficGen --> XBar --> CXLBridge (probe here) --> MemCtrl(DDR4)
#
# createLinear with block_size=64 touches every 64B word of every page it covers,
# so mean_unique_words must come out at exactly 64.0. Anything else means the
# probe is not seeing the request stream it claims to see.

import m5
from m5.objects import *

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
    hotskew_epoch=0,          # one epoch, closed at exit
    hotskew_topk=128,
    hotskew_budgets=[128, 512, 2048],
)

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR4_2400_8x8(range=system.mem_ranges[0])

system.gen.port = system.xbar.cpu_side_ports
system.system_port = system.xbar.cpu_side_ports
system.xbar.mem_side_ports = system.cxl.cpu_side_port
system.cxl.mem_side_port = system.mem_ctrl.port

root = Root(full_system=False, system=system)
m5.instantiate()

SWEEP = 16 * 1024 * 1024          # 16 MB == 4096 pages
def trace():
    yield system.gen.createLinear(200000000, 0, SWEEP, 64, 1000, 1000, 100, 0)
    yield system.gen.createExit(0)

system.gen.start(trace())
event = m5.simulate()
print("exiting @ tick", m5.curTick(), "because", event.getCause())
print("expected pages:", SWEEP // 4096, " expected words/page: 64.0")
