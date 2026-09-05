/*
 * synth.c -- synthetic workloads with analytically known word-density.
 *
 * The point of these is calibration, not performance. Each mode touches a number of
 * 64 B words per 4 KB page that we can compute on paper, so running hotskew against
 * them tells us whether the tool reports the truth. If `stride` mode with S=4096
 * does not come back with "1 unique word per page", nothing downstream is
 * trustworthy.
 *
 * Build: gcc -O1 -o synth synth.c
 *   (-O1, not -O2: we do not want the compiler vectorising or eliminating the
 *    access pattern we are trying to measure.)
 *
 * Usage: ./synth <mode> <mib> [param]
 *
 *   dense   <mib>            every byte, sequentially   -> 64/64 words per page
 *   stride  <mib> <bytes>    one byte every <bytes>     -> 4096/<bytes> words per page
 *   hotset  <mib> <pct>      <pct>% of pages get all 64 words, rest get 1
 *   zipf    <mib> <theta>    Zipfian 8 B accesses, the "realistic skew" case
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

static volatile uint64_t sink;

static void die(const char *m) {
    fprintf(stderr, "synth: %s\n", m);
    exit(1);
}

/* Every 64 B word of every page, in order. Expect mean_unique_words = 64. */
static void dense(uint8_t *buf, size_t n, int reps) {
    uint64_t s = 0;
    for (int r = 0; r < reps; ++r)
        for (size_t i = 0; i < n; i += 64) s += buf[i];
    sink = s;
}

/* One access every `stride` bytes. With stride S >= 64 and S dividing 4096, each
 * 4 KB page sees exactly 4096/S distinct words. */
static void strided(uint8_t *buf, size_t n, size_t stride, int reps) {
    uint64_t s = 0;
    for (int r = 0; r < reps; ++r)
        for (size_t i = 0; i < n; i += stride) s += buf[i];
    sink = s;
}

/* A `pct`% subset of pages is walked densely; the remainder gets a single word.
 * Models "a few dense hot pages among many sparse ones" -- M5's motivating mix. */
static void hotset(uint8_t *buf, size_t n, int pct, int reps) {
    const size_t pages = n / 4096;
    uint64_t s = 0;
    for (int r = 0; r < reps; ++r) {
        for (size_t p = 0; p < pages; ++p) {
            uint8_t *page = buf + p * 4096;
            if ((int)((p * 100) / pages) % 100 < pct) {
                for (size_t w = 0; w < 4096; w += 64) s += page[w];
            } else {
                s += page[0];
            }
        }
    }
    sink = s;
}

/* Zipfian 8 B accesses over the whole buffer. No analytic word count, but it is the
 * pattern that Redis/Memcached-style key-value lookups approximate, and it should
 * land between `dense` and `stride 4096`. */
static void zipf(uint8_t *buf, size_t n, double theta, uint64_t nacc) {
    const size_t items = n / 8;
    /* Precompute the normalisation constant for the harmonic-ish sum. */
    double zeta = 0.0;
    for (size_t i = 1; i <= items; ++i) zeta += 1.0 / pow((double)i, theta);

    uint64_t rng = 0x9E3779B97F4A7C15ULL;
    uint64_t s = 0;
    for (uint64_t k = 0; k < nacc; ++k) {
        rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17;
        double u = (double)(rng >> 11) / 9007199254740992.0;
        /* Inverse-CDF by scan is too slow; use the standard Gray et al. approximation. */
        double zetan = zeta;
        double eta = (1.0 - pow(2.0 / (double)items, 1.0 - theta)) /
                     (1.0 - (1.0 / zetan));
        double uz = u * zetan;
        size_t idx;
        if (uz < 1.0) idx = 0;
        else if (uz < 1.0 + pow(0.5, theta)) idx = 1;
        else idx = (size_t)((double)items * pow(eta * u - eta + 1.0, 1.0 / (1.0 - theta)));
        if (idx >= items) idx = items - 1;
        s += ((uint64_t *)buf)[idx];
    }
    sink = s;
}

/* ------------------------------------------------------------------------
 * Region of interest.
 *
 * Everything we actually want to measure happens inside synth_roi(). Run the
 * pintool with `-roi_rtn synth_roi` and the buffer allocation and the memset that
 * first-touches every page stay outside the measurement window. That matters a
 * lot: the memset writes every 64 B word of every page, so counting it would make
 * every workload look perfectly dense regardless of what it does afterwards.
 *
 * Marked noinline so the symbol survives -O1 and Pin can find it.
 * ------------------------------------------------------------------------ */
__attribute__((noinline)) void synth_roi(const char *mode, uint8_t *buf, size_t n,
                                         long param_i, double param_f, int reps) {
    if (strcmp(mode, "dense") == 0) {
        dense(buf, n, reps);
    } else if (strcmp(mode, "stride") == 0) {
        strided(buf, n, (size_t)param_i, reps);
    } else if (strcmp(mode, "hotset") == 0) {
        hotset(buf, n, (int)param_i, reps);
    } else if (strcmp(mode, "zipf") == 0) {
        zipf(buf, n, param_f, (uint64_t)(n / 8) * (uint64_t)reps);
    } else {
        die("unknown mode");
    }
    __asm__ __volatile__("" ::: "memory");
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr,
                "usage: %s dense|stride|hotset|zipf <mib> [param] [reps]\n"
                "  dense  <mib>            64/64 words per page\n"
                "  stride <mib> <bytes>    4096/<bytes> words per page\n"
                "  hotset <mib> <pct>      <pct>%% dense pages, rest 1 word\n"
                "  zipf   <mib> <theta>    skewed 8 B accesses\n"
                "\nProfile with: pin -t hotskew.so -roi_rtn synth_roi -- %s ...\n",
                argv[0], argv[0]);
        return 1;
    }

    const char *mode = argv[1];
    size_t mib = (size_t)atoll(argv[2]);
    if (mib == 0) die("size must be > 0 MiB");
    size_t n = mib * 1024 * 1024;

    long param_i = (argc > 3) ? atol(argv[3]) : 4096;
    double param_f = (argc > 3) ? atof(argv[3]) : 0.99;
    int reps = (argc > 4) ? atoi(argv[4]) : 4;
    if (strcmp(mode, "stride") == 0 && param_i <= 0) die("stride must be > 0");

    uint8_t *buf = NULL;
    if (posix_memalign((void **)&buf, 4096, n) != 0 || !buf) die("allocation failed");
    memset(buf, 1, n); /* first-touch, outside the ROI */

    synth_roi(mode, buf, n, param_i, param_f, reps);

    printf("synth %s %zu MiB done (sink=%llu)\n", mode, mib, (unsigned long long)sink);
    free(buf);
    return 0;
}
