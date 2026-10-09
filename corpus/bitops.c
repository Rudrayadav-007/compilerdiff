#include <stdio.h>

int main(void) {
    unsigned int x = 0xF0F0u;
    printf("shr=%u\n", x >> 4);
    printf("shl=%u\n", x << 4);
    printf("and=%u\n", x & 0xFFu);
    printf("xor=%u\n", x ^ 0xFFFFu);
    printf("not16=%u\n", ~x & 0xFFFFu);
    int ones = 0;
    for (unsigned int v = x; v != 0; v >>= 1) ones += (int)(v & 1u);
    printf("popcount=%d\n", ones);
    return 0;
}
