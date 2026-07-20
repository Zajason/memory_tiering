# 1. CXL Basics

## The problem CXL solves

Server memory capacity is stuck. You can only put so many DIMMs per socket, DDR pin counts don't
scale, and buying more capacity means buying more CPUs you don't need ("stranded" cores and
"stranded" memory in cloud fleets — Microsoft/Azure reported ~25% of DRAM stranded).

CXL (Compute Express Link) rides on the PCIe physical layer but adds cache-coherent protocols. The
relevant one here is **CXL.mem**: the CPU can issue plain loads and stores to memory that physically
lives on a card on the PCIe bus, and the hardware handles coherence.

Three protocol sub-layers:
- **CXL.io** — basically PCIe. Enumeration, config, DMA. How the device is discovered.
- **CXL.cache** — device caching host memory (accelerators). Not relevant to you.
- **CXL.mem** — host accessing device memory. **This is your protocol.**

Device types: Type 1 (accelerator, no memory), Type 2 (accelerator with memory), **Type 3 (memory
expander — a dumb box of DRAM)**. All three papers target Type 3.

## Why it's slow

A load that misses LLC and goes to CXL memory pays:

```
CPU core → LLC miss → Home Agent → CXL Root Complex
   → M2S packetization (Master-to-Subordinate)
   → PCIe SERDES + link traversal
   → device controller de-packetization
   → device-side DRAM controller → DRAM array
   → and the whole way back (S2M)
```

Rough numbers to memorize:

| Path | Idle latency | Bandwidth per link |
|---|---|---|
| Local DDR5 | ~80–100 ns | ~30–50 GB/s per channel |
| Remote NUMA socket | ~140–180 ns | — |
| CXL memory (x8 Gen5) | ~250–400 ns | ~25–30 GB/s |

So: **~2–3× the latency, and bandwidth capped by the link width, not by DRAM.** The DRAM on the card
might be perfectly fast DDR5; the interconnect is the tax. That asymmetry is the entire reason
tiering exists.

Also note the shape of the penalty: it's mostly *fixed latency*, not reduced throughput. That matters
— latency-bound pointer-chasing workloads suffer badly, streaming/bandwidth-bound workloads barely
notice (and can even *benefit*, because CXL bandwidth is additive to DDR bandwidth).

## How the OS sees it

The standard exposure is a **CPU-less NUMA node**: a NUMA node with memory but zero cores. The
firmware describes it via ACPI tables:

- **CEDT** — CXL Early Discovery Table, describes the CXL host bridges
- **SRAT** — System Resource Affinity Table, declares the memory range as its own proximity domain
- **HMAT** — Heterogeneous Memory Attribute Table, advertises latency/bandwidth so the kernel knows
  it's *slow*, not just *far*

Then `numactl -H` shows node 0 (CPUs + DDR) and node 1 (no CPUs, CXL DRAM), and existing NUMA
machinery — `migrate_pages`, AutoNUMA, and the newer tiering code in `mm/memory-tiers.c` — can be
pointed at it. This is why "CXL tiering" ends up being mostly a Linux memory-management story.

The alternative exposure is **hardware-managed / transparent**: the CPU's memory controller treats
local DRAM as a cache in front of CXL memory and the OS sees one flat address space. That's Intel
Flat Memory Mode — see [04-paper-memstrata.md](04-paper-memstrata.md).

## Terms you'll trip over

- **zNUMA node** — a "zero-CPU" NUMA node. Same thing as CPU-less node. CXLRAMSim uses this term.
- **HDM** — Host-managed Device Memory. The device DRAM as mapped into host physical address space.
- **M2S / S2M** — Master-to-Subordinate / Subordinate-to-Master. The CXL.mem request/response
  channels. In the simulator these are where you'd add latency.
- **Interleaving** — striping the physical address space across DDR and CXL (e.g. 1:1 or 2:1) so you
  get aggregate bandwidth. Note this *defeats* tiering: if addresses are interleaved you can't
  choose where a page lives.

## Sanity check before moving on

- [ ] I can name the three CXL protocol sub-layers and say which one matters here.
- [ ] I can explain why CXL latency is high even though the DRAM on the card is normal DDR5.
- [ ] I know what a CPU-less NUMA node is and which ACPI table advertises its slowness.
- [ ] I understand why latency-bound and bandwidth-bound workloads react differently.
