/*
 * zipf_client.c -- minimal YCSB-workload-C driver for Redis, no JVM required.
 *
 * Implements the part of YCSB that determines the memory access pattern:
 *   - a keyspace of N records, keys formatted exactly as YCSB does ("user<id>")
 *   - values of a fixed size, as YCSB's default 10 fields x 100 bytes
 *   - a load phase that SETs every key
 *   - a query phase of 100% GETs with Zipfian-distributed key popularity
 *
 * It does not implement YCSB's latency reporting, multiple workload profiles, or
 * its exact hashing of key ids to the keyspace. Throughput from this driver is not
 * comparable to a YCSB number and must not be reported as one. What it does
 * reproduce faithfully is the *distribution of memory accesses inside the server*,
 * which is the only thing Figure 4 depends on.
 *
 * The Zipfian generator is the Gray et al. formulation YCSB itself uses
 * (ScrambledZipfianGenerator's underlying ZipfianGenerator), so the popularity
 * skew matches.
 *
 * Build: cc -O2 -o zipf_client zipf_client.c -lm
 * Usage: ./zipf_client <host> <port> <records> <ops> [theta]
 *
 * Between the load and query phases it issues  ECHO HOTSKEW_ROI_BEGIN , and after
 * the query phase  ECHO HOTSKEW_ROI_END . setup_redis.sh patches redis-server to
 * call the hotskew ROI markers when it sees those, so the measurement covers the
 * query phase only and not the multi-gigabyte load.
 */

#include <arpa/inet.h>
#include <math.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define VALUE_BYTES 1000 /* YCSB default: 10 fields x 100 bytes */
#define PIPELINE 64

static int sock_connect(const char *host, int port) {
    struct sockaddr_in a;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    int one = 1;
    setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
    memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET;
    a.sin_port = htons((uint16_t)port);
    if (inet_pton(AF_INET, host, &a.sin_addr) != 1) {
        struct hostent *h = gethostbyname(host);
        if (!h) { close(fd); return -1; }
        memcpy(&a.sin_addr, h->h_addr_list[0], sizeof(a.sin_addr));
    }
    if (connect(fd, (struct sockaddr *)&a, sizeof(a)) != 0) { close(fd); return -1; }
    return fd;
}

/* ---- RESP reply draining ----
 *
 * Counting newlines is not good enough. "+OK\r\n" is one reply and one newline, but
 * a GET reply is "$1000\r\n" followed by 1000 bytes and "\r\n" -- two newlines for
 * one reply. A newline-counting drain returns after half the replies it was asked
 * for, the unread remainder accumulates in the socket buffer, and eventually the
 * server blocks on a full send buffer while we block waiting for it. The failure
 * looks like a hang partway through the run.
 *
 * So parse properly. Only the reply types Redis can send for SET/GET/ECHO are
 * handled: simple string, error, integer, and bulk string (including the $-1 null).
 */

#define RBUF_CAP (1 << 20)

typedef struct {
    char buf[RBUF_CAP];
    size_t len;   /* bytes held */
    size_t start; /* parse cursor */
} respbuf_t;

/* Find the CRLF ending the line at [from, len). Returns its offset or (size_t)-1. */
static size_t find_crlf(const respbuf_t *b, size_t from) {
    for (size_t i = from; i + 1 < b->len; ++i)
        if (b->buf[i] == '\r' && b->buf[i + 1] == '\n') return i;
    return (size_t)-1;
}

/* Try to consume one complete reply from the front of the buffer.
 * Returns 1 if one was consumed, 0 if more bytes are needed, -1 on protocol error. */
static int try_one_reply(respbuf_t *b) {
    if (b->start >= b->len) return 0;
    const char type = b->buf[b->start];
    size_t crlf = find_crlf(b, b->start);
    if (crlf == (size_t)-1) return 0;

    if (type == '+' || type == '-' || type == ':') {
        b->start = crlf + 2;
        return 1;
    }
    if (type == '$') {
        long n = strtol(&b->buf[b->start + 1], NULL, 10);
        if (n < 0) { /* null bulk string, $-1 */
            b->start = crlf + 2;
            return 1;
        }
        size_t need = crlf + 2 + (size_t)n + 2;
        if (b->len < need) return 0;
        b->start = need;
        return 1;
    }
    return -1; /* we never issue commands that reply with an array */
}

/* Consume exactly n replies. */
static int drain_n(int fd, respbuf_t *b, int n) {
    int done = 0;
    while (done < n) {
        int r = try_one_reply(b);
        if (r == 1) { ++done; continue; }
        if (r < 0) { fprintf(stderr, "protocol error in reply stream\n"); return -1; }

        /* Need more bytes. Compact first so a long reply always fits. */
        if (b->start > 0) {
            memmove(b->buf, b->buf + b->start, b->len - b->start);
            b->len -= b->start;
            b->start = 0;
        }
        if (b->len == RBUF_CAP) { fprintf(stderr, "reply larger than buffer\n"); return -1; }
        ssize_t got = recv(fd, b->buf + b->len, RBUF_CAP - b->len, 0);
        if (got <= 0) return -1;
        b->len += (size_t)got;
    }
    return 0;
}

/* ---- Zipfian, as in YCSB's ZipfianGenerator (Gray et al. "Quickly generating
 * billion-record synthetic databases"). theta=0.99 is the YCSB default. ---- */
typedef struct {
    unsigned long n;
    double theta, zetan, alpha, eta;
    unsigned long long rng;
} zipf_t;

static double zeta(unsigned long n, double theta) {
    double s = 0.0;
    for (unsigned long i = 1; i <= n; ++i) s += 1.0 / pow((double)i, theta);
    return s;
}

static void zipf_init(zipf_t *z, unsigned long n, double theta, unsigned long long seed) {
    z->n = n;
    z->theta = theta;
    z->zetan = zeta(n, theta);
    double zeta2 = zeta(2, theta);
    z->alpha = 1.0 / (1.0 - theta);
    z->eta = (1.0 - pow(2.0 / (double)n, 1.0 - theta)) / (1.0 - zeta2 / z->zetan);
    z->rng = seed ? seed : 0x9E3779B97F4A7C15ULL;
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

static int send_all(int fd, const char *buf, size_t len);

/* Send  ECHO <marker>  with a correctly computed RESP bulk length. */
static int send_marker(int fd, respbuf_t *b, const char *marker) {
    char buf[256];
    int n = snprintf(buf, sizeof(buf), "*2\r\n$4\r\nECHO\r\n$%zu\r\n%s\r\n",
                     strlen(marker), marker);
    if (send_all(fd, buf, (size_t)n) != 0) return -1;
    return drain_n(fd, b, 1);
}

static int send_all(int fd, const char *buf, size_t len) {
    while (len) {
        ssize_t w = send(fd, buf, len, 0);
        if (w <= 0) return -1;
        buf += w;
        len -= (size_t)w;
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 5) {
        fprintf(stderr,
                "usage: %s <host> <port> <records> <ops> [theta]\n"
                "  records: keyspace size (YCSB recordcount)\n"
                "  ops    : GET operations in the query phase\n"
                "  theta  : Zipfian skew, default 0.99 (YCSB default)\n",
                argv[0]);
        return 1;
    }
    const char *host = argv[1];
    int port = atoi(argv[2]);
    unsigned long records = strtoul(argv[3], NULL, 10);
    unsigned long ops = strtoul(argv[4], NULL, 10);
    double theta = (argc > 5) ? atof(argv[5]) : 0.99;

    int fd = sock_connect(host, port);
    if (fd < 0) { perror("connect"); return 1; }

    static respbuf_t rb;
    rb.len = rb.start = 0;

    char *value = malloc(VALUE_BYTES + 1);
    memset(value, 'v', VALUE_BYTES);
    value[VALUE_BYTES] = 0;

    /* ---- load phase ---- */
    fprintf(stderr, "loading %lu records x %d B (~%.1f GB of values)\n", records, VALUE_BYTES,
            (double)records * VALUE_BYTES / 1e9);
    char cmd[VALUE_BYTES + 256];
    int outstanding = 0;
    for (unsigned long i = 0; i < records; ++i) {
        int n = snprintf(cmd, sizeof(cmd),
                         "*3\r\n$3\r\nSET\r\n$%d\r\nuser%lu\r\n$%d\r\n%s\r\n",
                         (int)(4 + snprintf(NULL, 0, "%lu", i)), i, VALUE_BYTES, value);
        if (send_all(fd, cmd, (size_t)n) != 0) { perror("send"); return 1; }
        if (++outstanding == PIPELINE) {
            if (drain_n(fd, &rb, outstanding) != 0) { fprintf(stderr, "server closed\n"); return 1; }
            outstanding = 0;
        }
        if ((i % 200000) == 0 && i) fprintf(stderr, "  %lu / %lu\n", i, records);
    }
    if (outstanding && drain_n(fd, &rb, outstanding) != 0) return 1;

    /* ---- ROI begin ----
     * Sent as an ECHO with a distinctive payload. benchmarks/patches/redis-roi.patch
     * makes redis-server call hotskew_roi_begin()/end() when it sees these, so the
     * measurement covers the query phase only and not the multi-gigabyte load.
     * Lengths are computed, never hardcoded: a wrong RESP bulk length desynchronises
     * the connection and the failure looks like a hang. */
    send_marker(fd, &rb, "HOTSKEW_ROI_BEGIN");
    fprintf(stderr, "load done; starting %lu Zipfian GETs (theta=%.2f)\n", ops, theta);

    /* ---- query phase: 100% read, Zipfian ---- */
    zipf_t z;
    zipf_init(&z, records, theta, 12345);
    outstanding = 0;
    for (unsigned long i = 0; i < ops; ++i) {
        unsigned long k = zipf_next(&z);
        int n = snprintf(cmd, sizeof(cmd), "*2\r\n$3\r\nGET\r\n$%d\r\nuser%lu\r\n",
                         (int)(4 + snprintf(NULL, 0, "%lu", k)), k);
        if (send_all(fd, cmd, (size_t)n) != 0) { perror("send"); return 1; }
        if (++outstanding == PIPELINE) {
            if (drain_n(fd, &rb, outstanding) != 0) { fprintf(stderr, "server closed\n"); return 1; }
            outstanding = 0;
        }
    }
    if (outstanding && drain_n(fd, &rb, outstanding) != 0) return 1;

    send_marker(fd, &rb, "HOTSKEW_ROI_END");

    fprintf(stderr, "done\n");
    free(value);
    close(fd);
    return 0;
}
