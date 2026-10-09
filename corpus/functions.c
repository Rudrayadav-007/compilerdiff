#include <stdio.h>

static int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }

static int power(int base, int exp) {
    int r = 1;
    while (exp-- > 0) r *= base;
    return r;
}

static int factorial(int n) { return n <= 1 ? 1 : n * factorial(n - 1); }

static int is_prime(int n) {
    if (n < 2) return 0;
    for (int d = 2; d * d <= n; d++)
        if (n % d == 0) return 0;
    return 1;
}

int main(void) {
    printf("gcd=%d\n", gcd(48, 18));
    printf("pow=%d\n", power(2, 10));
    printf("fact5=%d\n", factorial(5));
    int count = 0;
    for (int i = 0; i < 50; i++) count += is_prime(i);
    printf("primes_below_50=%d\n", count);
    return 0;
}
