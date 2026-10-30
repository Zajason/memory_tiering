## 1. How hot is a hot page?

40 seconds. This course research project was carried out for Advanced Computer Architecture with CSLab. The target is M5 Figure 4, not a complete implementation of M5. Present the measurement method, discrepancies and controlled extensions.

Sources: docs/methodology.md

## 2. The assignment

50 seconds. Record memory references, use the artifact benchmarks, reproduce the figure and extend it to accesses. Memstrata and NeoMem also informed the study. Figure 4 concerns spatial coverage, not the hot-page selection accuracy in Figure 3.

Sources: docs/methodology.md

## 3. 4 KiB = 64 lines x 64 B

70 seconds. Count distinct lines for each page and window. The CDF at N is the fraction of observations touching at most N lines. Coverage is not access frequency. Each page-window observation has equal weight; epochs are not weighted equally regardless of population.

Sources: docs/methodology.md

## 4. A custom pintool for the measurement

70 seconds. Intel supplies the Pin framework. Our C++ implementation instruments memory operands, splits them into lines, filters them through caches and updates masks and counters. It does not retain a full trace. ROI hooks, shared epochs and manifests support validation and reproducibility.

Sources: src/profiler/pintool/hotskew.cpp; counter_table.hpp; paired_observer.hpp

## 5. Pin accesses vs device-side traffic

70 seconds. A cache model is needed as a filter. It has private L1/L2, a shared LLC, writeback/write-allocate, LRU and non-inclusive behavior. It is not an exact Sapphire Rapids simulator. Pin sees virtual user-space operands, not kernel copies or hardware prefetches.

Sources: docs/methodology.md

## 6. Shared windows, different streams

70 seconds. Accesses are demand operands split by line. Fills are demand misses through every modeled cache level. Total traffic adds dirty LLC writebacks. All streams share boundaries in the same execution. The protocol uses 10M memory events, retains the final partial window and reports a separate whole-ROI union. Controls vary only declared factors.

Sources: docs/methodology.md

## 7. Common baseline: M5 / accesses / misses

80 seconds. Top: digitized M5. Below: paired accesses and demand misses under a common protocol. This baseline precedes the new input campaign. It is not full replication. Retain it as the common basis for comparing controls.

Sources: docs/uniform-windows.md

## 8. New inputs, unchanged measurement protocol

70 seconds. The new campaign uses our declared Twitter reductions and Google+ snapshots 4/2. All six runs completed and passed checks. These are not the exact author inputs. Negative results are retained: BC and SSSP disagree more strongly.

Sources: docs/fidelity-followup.md

## 9. Agreement did not improve everywhere

50 seconds. Report the maximum absolute discrepancy across all five N thresholds, not just the tail. Do not substitute whole-ROI results because they look closer. The input campaign tests a hypothesis; it does not establish successful full reproduction.

Sources: results/fidelity-2026-10-27/scores.csv

## 10. Why do accesses and misses look alike?

60 seconds. Touching a line sets one bit regardless of repeated hits. With cold initial caches, the first demand touch causes a fill, so whole-ROI line coverage can agree. This does not mean caches are ineffective. Baseline BFS has about 168.8M accesses and 7.9M fills.

Sources: docs/methodology.md

## 11. Declared controls and exploratory results

60 seconds. Do not choose a separate protocol for each workload after inspecting M5. Stage 2 declares full-process collection, real inputs with twenty threads, nine LLC ways and RSS-selected TC. Select the footprint before looking at Pin CDFs. Closest cases are explicitly exploratory.

TC native RSS: 8.89 GB; target 5.0 GB. Within tolerance: false. Selection used RSS only. This is not a size-matched reproduction. The completed one-thread control has pooled miss error 53.87 pp, worse than 34.87 pp for the smaller input. The twenty-thread control is a separate experiment.

Sources: docs/pin-stage2-protocol.md

## 12. The same comparison in SimCXL

70 seconds. The probe measures physical accepted requests at the CXL bridge. Bridge and controller clocks are independent; never add their observations together. The overview compares different setups, not identical traces. All six graph workloads completed and passed checks. TC: 621,867,320 requests in 63 windows, 31.07 hours, maximum discrepancy 37.78 percentage points. PR is numerically close, but full reproduction is not established. Liblinear and BC window controls remain in the simulator queue.

Sources: docs/simulator-figure4.md

## 13. PAC / WAC and bounded trackers

60 seconds. Exact page/word counts provide ground truth. HPT/HWT are bounded trackers using Space-Saving and Count-Min plus top-K. Corrected runs completed. This is not the complete M5 hardware or tiering manager. Tracker N is a capacity budget, distinct from N in the CDF thresholds.

Sources: docs/revalidation-2026-10-25.md

## 14. Beyond the original figure

50 seconds. Validated extensions cover granularity, turnover and previous-window placement. A coarser tracking unit changes apparent density, not the physical cache-line size. Redis A/C, Memcached and Liblinear are included in the broader study. The serial latency cost model is not measured application speedup.

Sources: docs/revalidation-2026-10-25.md

## 15. What exact reproduction still requires

50 seconds. Correct implementation of our counters does not recover the exact reference procedure. We still need the reduced graphs, WAC collection schedule and page population. Controls continue, but the objective is to explain discrepancies without selecting attractive bars after the fact.

Sources: docs/m5-parameter-evidence.md
