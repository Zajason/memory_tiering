# Cache configurations

Each file here is sourced by `experiments/run_hotskew.sh` and sets the cache geometry
passed to the pintool.

The defaults are not invented. They are the **Intel Xeon Gold 6430 (Sapphire Rapids)**
in M5's own testbed, including M5's Intel CAT way-partitioning. Their setup scripts
(`setup/core_pqos/set_*_llc.sh` in the artifact) pin each workload class to a subset
of L3 ways:

| Workload class      | CAT mask | Ways (of 15) | LLC available | Config |
|---------------------|----------|--------------|---------------|--------|
| GAPBS, Liblinear (20 threads) | `0x7FC0` | 9 | 36 MB | `spr-20t.env` |
| SPEC CPU2017 (8 threads)      | `0x7800` | 4 | 16 MB | `spr-8t.env` |
| Redis (1 thread)              | `0x4000` | 1 |  4 MB | `spr-1t.env` |
| unpartitioned (reference)     | `0x7FFF` | 15 | 60 MB | `spr-full.env` |

This matters more than it looks. CAT partitions the L3 **by way**, not by set, so the
set count stays at 65536 in every case and only the associativity changes. Our cache
model is way-associative, so setting `L3_ASSOC` to the number of granted ways
reproduces M5's partitioning exactly rather than approximately.

It also explains a result that is otherwise surprising: Redis, the benchmark with the
most extreme sparsity in M5's Figure 4 (86% of pages with ≤25% of words touched), was
running with only **4 MB** of last-level cache. A small LLC lets more of a page's
traffic through to the memory controller, and the traffic that gets through is the
part with poor reuse — which is exactly the sparse part.

## Choosing a config

Match the config to the workload class you are imitating, not to the machine you are
running on. The pintool simulates the cache; the host's real cache is irrelevant to
the result. `HOST_THREADS` is the only host-dependent knob.

## Footprint ratio

The other half of the calibration is the ratio of working set to LLC. M5 used datasets
of up to 8 GB against a 36 MB partition — roughly 1:220. A small dataset on a big
modelled LLC will overstate sparsity, because the LLC absorbs the dense, high-reuse
pages entirely and only the sparse tail reaches memory. `experiments/scale_sweep.sh`
measures this sensitivity directly; see `docs/methodology.md`.
