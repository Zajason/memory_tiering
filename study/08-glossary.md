# 8. Glossary

Keep this open while reading. Ordered roughly by when you'll meet each term.

## CXL
- **CXL** — Compute Express Link. Cache-coherent interconnect over the PCIe PHY.
- **CXL.io / .cache / .mem** — the three sub-protocols. You care about **.mem**.
- **Type 3 device** — a memory expander. Dumb box of DRAM on the bus. Your target.
- **HDM** — Host-managed Device Memory. Device DRAM mapped into host physical address space.
- **M2S / S2M** — Master-to-Subordinate / Subordinate-to-Master. Request / response channels of
  CXL.mem. Where you tap for profiling.
- **Root Complex** — the host-side CXL controller.
- **cxl-cli** — userspace tool for configuring CXL regions/devices.
- **CEDT / SRAT / HMAT / MCFG / DSDT** — ACPI tables. CEDT describes CXL host bridges; SRAT declares
  proximity domains; **HMAT advertises latency/bandwidth so the OS knows the node is slow**.

## Tiering
- **Tier** — a class of memory with distinct performance. Here: local DDR (fast) and CXL (slow).
- **zNUMA / CPU-less NUMA node** — NUMA node with memory and no cores. How CXL memory is usually
  exposed.
- **Promotion** — migrate slow → fast. The hard one.
- **Demotion** — migrate fast → slow. The easy one (LRU is fine).
- **Hot / cold page** — frequently / infrequently accessed.
- **Hot set** — the set of pages currently hot. It *moves over time*; that's what makes this hard.
- **Ping-pong** — a page repeatedly promoted and demoted. Pure loss.
- **Migration quota** — bandwidth cap on migration, so migration doesn't eat the bandwidth it's
  trying to save. NeoMem default: 256 MB/s.
- **First-touch** — default NUMA policy: allocate on the node of the thread that first touches the
  page. The do-nothing baseline.
- **Internal fragmentation (in this context)** — the cold bytes you drag along when you migrate a
  whole page for a few hot lines.

## Profiling
- **PTE** — Page Table Entry. Its **Accessed bit** is set by the MMU on access.
- **PTE-scan** — clear access bits, wait, rescan. Coarse (1 bit) and slow (seconds).
- **Hint fault / NUMA hinting fault** — deliberately un-map a PTE so the next access traps and can
  be logged. Costs a page fault per sample. **Measures TLB misses, not LLC misses.**
- **PEBS / IBS** — Intel / AMD precise event sampling. Can sample LLC misses with addresses, but
  overhead scales with rate.
- **LLC miss** — last-level cache miss. **The event that actually determines CXL traffic.** The
  distinction from TLB misses is the crux of NeoMem's motivation.
- **Count-min sketch** — W×D counter array with D hash functions; estimate = min over lanes.
  Collisions only inflate, so min is the tightest bound. NeoMem's structure.
- **Top-K / heavy-hitter tracker** — bounded counter table that keeps the K most frequent items
  (Misra–Gries style). M5's structure, borrowed from Rowhammer defenses.
- **H3 hash** — a cheap, hardware-friendly family of universal hash functions.
- **Bloom filter** — probabilistic set-membership. NeoProf uses "hot bits" this way to avoid
  re-reporting an already-known-hot page.

## Linux MM
- **AutoNUMA / ANB** — NUMA Balancing. Hint-fault based.
- **TPP** — Transparent Page Placement (Meta, ASPLOS'23).
- **DAMON** — Data Access MONitor. Region-sampled PTE scanning.
- **Memtis** — SOSP'23, PEBS-driven tiering with a dynamic histogram threshold. Common baseline.
- **THP** — Transparent Huge Pages. 2 MB pages. Cheaper to migrate, much worse fragmentation.
- **LRU 2Q / MGLRU** — Linux page reclaim lists. NeoMem reuses 2Q for cold detection.
- **TLB shootdown** — IPI to other cores to invalidate a stale translation. Often the dominant cost
  of a page migration.
- **rmap** — reverse mapping: physical page → all PTEs that map it. Must be walked on migration.
- **RSS** — Resident Set Size. Physical memory a process actually occupies.

## Systems / hardware
- **Direct-mapped** — each address has exactly one possible slot. Cheap, but conflict misses.
- **Conflict miss** — a miss caused by two hot addresses mapping to the same slot despite free
  capacity elsewhere. Memstrata's core problem.
- **Page coloring** — choosing physical page frames so that their cache/slot mapping is controlled.
  Memstrata's fix.
- **Flat Memory Mode** — Intel's hardware-managed CXL tiering: local DRAM as a direct-mapped,
  line-granular, 1:1 cache in front of CXL memory. Transparent to the OS.
- **Near-memory cache** — general term for the above.
- **Stranded memory** — DRAM in a server that can't be allocated because the CPUs are all sold.
  ~25% in Azure's fleet. The economic motivation for the whole field.

## Simulation
- **gem5** — the full-system architectural simulator CXLRAMSim is built on.
- **Full-system (FS) mode** — boots a real OS. As opposed to syscall-emulation (SE) mode.
- **Ruby** — gem5's detailed memory/coherence model. Slower, more accurate. CXLRAMSim uses MESI
  two-level directory in Ruby.
- **Checkpoint** — saved simulator state. Boot once, restore many times. **Use these from day one.**
- **KIPS / MIPS** — simulated instructions per second. Your patience metric.

## Workloads
- **GUPS** — Giga-Updates Per Second. Random 8 B updates over a huge array. Zero locality; the
  adversarial case for page migration. Your best demo.
- **XSBench** — Monte Carlo particle transport proxy. Large random table lookups.
- **PageRank / BFS** — graph workloads. Irregular, pointer-chasing, shifting hot set.
- **Silo / YCSB-C** — in-memory DB with Zipfian-skewed reads. Extreme sub-page hotness.
- **Btree** — index lookups. Same story.
- **DeathStarBench** — microservice benchmark suite.
- **Zipfian** — skewed distribution: a few items get most of the accesses. Why tiering works at all.
