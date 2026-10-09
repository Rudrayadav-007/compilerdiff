#include <limits.h>
#include <stdio.h>

/* Returns 1 and stores a+b if it fits in int; returns 0 BEFORE any overflow can happen. */
static int safe_add(int a, int b, int *out) {
    if (b > 0 && a > INT_MAX - b) return 0;
    if (b < 0 && a < INT_MIN - b) return 0;
    *out = a + b;
    return 1;
}

static void show(const char *label, int a, int b) {
    int r = 0;
    if (safe_add(a, b, &r)) printf("%s=%d\n", label, r);
    else printf("%s=overflow\n", label);
}

int main(void) {
    show("add_max_1", INT_MAX, 1);
    show("add_max-1_1", INT_MAX - 1, 1);
    show("add_min_-1", INT_MIN, -1);
    show("add_min_max", INT_MIN, INT_MAX);
    printf("uzero_minus_1=%u\n", 0u - 1u);          /* unsigned wrap is defined */
    printf("abs_min_plus_1=%d\n", -(INT_MIN + 1));
    unsigned char c = 255;
    c++;                                              /* converts back to 0 */
    printf("uchar_inc=%d\n", c);
    unsigned char d = 255;
    int promoted = d + 1;                             /* promoted to int first */
    printf("promote=%d\n", promoted);
    return 0;
}
