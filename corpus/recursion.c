#include <stdio.h>

static int ackermann(int m, int n) {
    if (m == 0) return n + 1;
    if (n == 0) return ackermann(m - 1, 1);
    return ackermann(m - 1, ackermann(m, n - 1));
}

static int hanoi_moves(int n) { return n == 0 ? 0 : 2 * hanoi_moves(n - 1) + 1; }

static int fib(int n) { return n < 2 ? n : fib(n - 1) + fib(n - 2); }

static int digit_sum(int n) { return n == 0 ? 0 : n % 10 + digit_sum(n / 10); }

static int reverse_digits(int n) {
    int r = 0;
    while (n > 0) {
        r = r * 10 + n % 10;
        n /= 10;
    }
    return r;
}

int main(void) {
    printf("ackermann_2_3=%d\n", ackermann(2, 3));
    printf("hanoi_10=%d\n", hanoi_moves(10));
    printf("fib15=%d\n", fib(15));
    printf("digit_sum=%d\n", digit_sum(98765));
    printf("reverse=%d\n", reverse_digits(12345));
    return 0;
}
