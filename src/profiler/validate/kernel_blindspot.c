/*
 * kernel_blindspot.c -- demonstrate memory traffic that Pin structurally cannot see.
 *
 * Pin instruments the instructions the *application* executes. Memory the kernel
 * touches on the application's behalf -- the copy inside read(2), page-fault zeroing,
 * page-cache population, DMA -- involves no user-mode load or store, so no
 * instrumentation fires and the traffic is invisible.
 *
 * M5's PAC and WAC sit at the memory controller. They count all of it.
 *
 * This matters for the reproduction because GAPBS loads its CSR with file.read()
 * (reader.h:290-296), so a multi-gigabyte, perfectly dense, every-word-of-every-page
 * write is counted by M5's hardware and not by ours. That is one concrete, verified
 * reason our word-coverage numbers come out lower than the paper's.
 *
 * This program makes the effect measurable:
 *
 *   phase 1: read() a file of N bytes into a heap buffer  -- kernel does the copy
 *   phase 2: memcpy() the same N bytes in user space      -- we do the copy
 *
 * Both move the same number of bytes over the same buffers. Profile with the ROI on
 * each phase and compare the DRAM accesses hotskew reports. Phase 1 should report
 * almost nothing; phase 2 should report roughly N/64 accesses.
 *
 * Build: cc -O1 -o kernel_blindspot kernel_blindspot.c
 * Usage: ./kernel_blindspot <file> <mib> read|memcpy
 */

#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "../roi/hotskew_roi.h"

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr,
                "usage: %s <file> <mib> read|memcpy\n"
                "  read   : pull <mib> MiB in via read(2)   -- kernel-side copy\n"
                "  memcpy : copy <mib> MiB in user space    -- application-side\n",
                argv[0]);
        return 1;
    }
    const char *path = argv[1];
    size_t n = (size_t)atoll(argv[2]) * 1024 * 1024;
    const int do_read = (strcmp(argv[3], "read") == 0);

    char *dst = NULL, *src = NULL;
    if (posix_memalign((void **)&dst, 4096, n) != 0 || !dst) return 1;
    /* Fault the destination in before the ROI so page-fault work is not counted. */
    memset(dst, 0, n);

    if (do_read) {
        int fd = open(path, O_RDONLY);
        if (fd < 0) { perror("open"); return 1; }
        hotskew_roi_begin();
        size_t got = 0;
        while (got < n) {
            ssize_t r = read(fd, dst + got, n - got);
            if (r <= 0) break;
            got += (size_t)r;
        }
        hotskew_roi_end();
        close(fd);
        printf("read   %zu MiB via read(2)\n", got / (1024 * 1024));
    } else {
        if (posix_memalign((void **)&src, 4096, n) != 0 || !src) return 1;
        memset(src, 'x', n);
        hotskew_roi_begin();
        memcpy(dst, src, n);
        hotskew_roi_end();
        printf("memcpy %zu MiB in user space\n", n / (1024 * 1024));
        free(src);
    }

    /* Keep the buffer live so nothing is optimised away. */
    volatile char sink = dst[n - 1];
    (void)sink;
    free(dst);
    return 0;
}
