/*
 * hotskew_roi_m5.h -- the gem5 full-system counterpart of hotskew_roi.h.
 *
 * Why this file exists rather than a second patch
 * -----------------------------------------------
 * benchmarks/patches/gapbs-roi.patch inserts hotskew_roi_begin()/end() around the
 * timed kernel in BenchmarkKernel(). Under Pin those are empty symbols that the
 * tool attaches to. Under gem5 there is no external tool to attach anything, so the
 * marker has to *do* something: execute an m5 pseudo-instruction that the simulator
 * traps.
 *
 * Keeping the same function names means the **same patch, at the same call sites**,
 * drives both. The simulator therefore measures exactly the region Pin measured --
 * GAPBS's own "Trial Time" kernel, with graph construction, CSR building and
 * verification all outside it. If the ROIs differed, any disagreement between the
 * two instruments would be uninterpretable, because we would not know whether we
 * were looking at a real effect or at two different questions.
 *
 * Protocol with the run script
 * ----------------------------
 *   hotskew_roi_begin()  -> m5_exit(0)   : hand control back to the config script,
 *                                          which swaps the KVM CPU for the detailed
 *                                          TimingSimpleCPU and resumes.
 *   hotskew_roi_end()    -> m5_exit(0)   : second handback; the script stops and
 *                                          writes the probe summary.
 *
 * m5_exit is used rather than m5_work_begin because the CPU switch is what we
 * actually need, and work items require the workbegin/workend hooks to be
 * configured on the board. Both markers are idempotent from the guest's point of
 * view: the simulator resumes the guest exactly where it left off.
 *
 * Build: link against util/m5/build/x86/out/libm5.a and add util/m5/include to the
 * include path. Static linking is required -- the Ubuntu 18.04 guest image has an
 * older libstdc++ than this host.
 */

#ifndef HOTSKEW_ROI_H
#define HOTSKEW_ROI_H

#include <gem5/m5ops.h>

#ifdef __cplusplus
extern "C" {
#endif

__attribute__((noinline, weak, used)) void hotskew_roi_begin(void) {
    __asm__ __volatile__("" ::: "memory");
    m5_exit(0);
    __asm__ __volatile__("" ::: "memory");
}

__attribute__((noinline, weak, used)) void hotskew_roi_end(void) {
    __asm__ __volatile__("" ::: "memory");
    m5_exit(0);
    __asm__ __volatile__("" ::: "memory");
}

#ifdef __cplusplus
}
#endif

#endif /* HOTSKEW_ROI_H */
