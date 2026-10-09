#include <limits.h>
#include <stdio.h>

int main(void) {
    printf("int_max=%d\n", INT_MAX);
    printf("int_min=%d\n", INT_MIN);
    printf("uint_max=%u\n", UINT_MAX);
    /* Unsigned arithmetic wraps by definition; no UB. */
    unsigned int u = UINT_MAX;
    printf("uint_wrap=%u\n", u + 1u);
    /* Widen BEFORE adding so there is no signed overflow. */
    long long wide = (long long)INT_MAX + 1;
    printf("int_max_plus_1=%lld\n", wide);
    printf("schar_max=%d\n", SCHAR_MAX);
    printf("int_max_minus_1=%d\n", INT_MAX - 1);
    return 0;
}
