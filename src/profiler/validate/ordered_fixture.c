#include <stdint.h>

static volatile uint64_t data[2 * 1024 * 1024] __attribute__((aligned(4096)));
static volatile uint64_t sink;

__attribute__((noinline)) void hotskew_roi_begin(void) { __asm__ volatile("" ::: "memory"); }
__attribute__((noinline)) void hotskew_roi_end(void) { __asm__ volatile("" ::: "memory"); }

int main(void) {
    for (int trial = 0; trial < 2; ++trial) {
        hotskew_roi_begin();
        uint64_t sum = 0;
        for (int pass = 0; pass < 3; ++pass)
            for (unsigned i = 0; i < sizeof(data) / sizeof(data[0]); i += 8) {
                sum += data[i];
                data[i] = sum + i;
            }
        sink = sum;
        hotskew_roi_end();
    }
    return 0;
}
