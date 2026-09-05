/*
 * zipf_selftest.c -- check that zipf_client.c's key generator is actually skewed.
 *
 * The whole reason Redis shows sub-page sparsity is that its key popularity is
 * heavily skewed: a small hot set is read constantly while most of the keyspace is
 * cold, so a 4 KB page holding several values has only the hot ones touched. If the
 * generator were uniform by mistake, the run would produce a dense result and the
 * error would look like a finding.
 *
 * This duplicates the generator from zipf_client.c verbatim and reports the
 * popularity concentration, so a bad edit is caught immediately.
 *
 * Build: cc -O2 -o zipf_selftest zipf_selftest.c -lm
 *
 * Expected for theta=0.99 (YCSB's default): roughly 20-25% of accesses land in the
 * top 0.1% of the keyspace, and the top 10% takes over half.
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    unsigned long n;
    double theta, zetan, alpha, eta;
    unsigned long long rng;
} zipf_t;

static double zeta(unsigned long n, double t) {
    double s = 0.0;
    for (unsigned long i = 1; i <= n; ++i) s += 1.0 / pow((double)i, t);
    return s;
}

static void zipf_init(zipf_t *z, unsigned long n, double t, unsigned long long sd) {
    z->n = n;
    z->theta = t;
    z->zetan = zeta(n, t);
    double z2 = zeta(2, t);
    z->alpha = 1.0 / (1.0 - t);
    z->eta = (1.0 - pow(2.0 / (double)n, 1.0 - t)) / (1.0 - z2 / z->zetan);
    z->rng = sd ? sd : 0x9E3779B97F4A7C15ULL;
}

static double next_double(zipf_t *z) {
    z->rng ^= z->rng << 13;
    z->rng ^= z->rng >> 7;
    z->rng ^= z->rng << 17;
    return (double)(z->rng >> 11) / 9007199254740992.0;
}

static unsigned long zipf_next(zipf_t *z) {
    double u = next_double(z);
    double uz = u * z->zetan;
    if (uz < 1.0) return 0;
    if (uz < 1.0 + pow(0.5, z->theta)) return 1;
    unsigned long r = (unsigned long)((double)z->n * pow(z->eta * u - z->eta + 1.0, z->alpha));
    return r >= z->n ? z->n - 1 : r;
}

static int desc(const void *a, const void *b) {
    unsigned long x = *(const unsigned long *)a, y = *(const unsigned long *)b;
    return (x < y) ? 1 : ((x > y) ? -1 : 0);
}

int main(int argc, char **argv) {
    unsigned long n = (argc > 1) ? strtoul(argv[1], NULL, 10) : 100000;
    unsigned long ops = (argc > 2) ? strtoul(argv[2], NULL, 10) : 2000000;
    double theta = (argc > 3) ? atof(argv[3]) : 0.99;

    zipf_t z;
    zipf_init(&z, n, theta, 12345);
    unsigned long *c = calloc(n, sizeof(unsigned long));
    if (!c) return 1;
    unsigned long distinct = 0;
    for (unsigned long i = 0; i < ops; ++i) {
        unsigned long k = zipf_next(&z);
        if (!c[k]) ++distinct;
        c[k]++;
    }
    qsort(c, n, sizeof(unsigned long), desc);

    printf("zipf theta=%.2f  keyspace=%lu  ops=%lu\n", theta, n, ops);
    const double pcts[] = {0.1, 1.0, 5.0, 10.0, 50.0};
    int fail = 0;
    for (int i = 0; i < 5; ++i) {
        unsigned long k = (unsigned long)((double)n * pcts[i] / 100.0);
        if (!k) k = 1;
        unsigned long s = 0;
        for (unsigned long j = 0; j < k; ++j) s += c[j];
        printf("  top %5.1f%% of keys -> %5.1f%% of accesses\n", pcts[i], 100.0 * s / ops);
        if (pcts[i] == 10.0 && (100.0 * s / ops) < 40.0) fail = 1;
    }
    printf("  distinct keys touched: %lu of %lu (%.1f%%)\n", distinct, n,
           100.0 * distinct / n);
    if (fail) {
        printf("\nFAIL: the distribution is not skewed enough to be Zipfian.\n");
        return 1;
    }
    printf("\nPASS: distribution is skewed as expected.\n");
    free(c);
    return 0;
}
