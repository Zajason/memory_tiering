/*
 * hotskew_roi.h -- region-of-interest markers for the hotskew pintool.
 *
 * Why a marker is needed
 * ----------------------
 * Real benchmarks spend most of their memory traffic outside the part we care
 * about. GAPBS builds and sorts a CSR graph before it runs a single BFS step;
 * Redis loads the whole dataset before serving a query. That setup traffic
 * sequentially writes every 64 B word of every page it allocates, so including it
 * makes *every* workload look perfectly dense and the measurement says nothing.
 *
 * M5 sidesteps this in hardware -- they start the FPGA counters at "10 different
 * random execution points" during steady state (ASPLOS'25, Sec. 4.1). We do the
 * equivalent by bracketing the steady-state region explicitly.
 *
 * Usage
 * -----
 *   #include "hotskew_roi.h"
 *   ...
 *   hotskew_roi_begin();
 *   run_the_kernel();
 *   hotskew_roi_end();
 *
 * Then run:  pin -t hotskew.so -roi_begin hotskew_roi_begin -roi_end hotskew_roi_end -- ./app
 *
 * The functions are empty. They exist only so that the compiler emits a symbol at a
 * known point in the instruction stream for Pin to attach to. `noinline` and `weak`
 * keep the symbol alive under -O3 and let the header be included from several
 * translation units without a duplicate-definition error. The memory clobber stops
 * the compiler moving loads and stores across the marker.
 *
 * Cost when not profiling: one call to an empty function per region. Unmeasurable.
 */

#ifndef HOTSKEW_ROI_H
#define HOTSKEW_ROI_H

#ifdef __cplusplus
extern "C" {
#endif

__attribute__((noinline, weak, used)) void hotskew_roi_begin(void) {
    __asm__ __volatile__("" ::: "memory");
}

__attribute__((noinline, weak, used)) void hotskew_roi_end(void) {
    __asm__ __volatile__("" ::: "memory");
}

#ifdef __cplusplus
}
#endif

#endif /* HOTSKEW_ROI_H */
