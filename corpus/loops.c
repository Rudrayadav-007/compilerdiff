#include <stdio.h>

int main(void) {
    int sum = 0;
    for (int i = 1; i <= 100; i++) sum += i;
    printf("sum=%d\n", sum);

    long fact = 1;
    for (int i = 2; i <= 10; i++) fact *= i;
    printf("fact10=%ld\n", fact);

    int prev = 0, cur = 1;
    for (int i = 0; i < 20; i++) {
        int next = prev + cur;
        prev = cur;
        cur = next;
    }
    printf("fib20=%d\n", prev);

    int n = 27, steps = 0;
    while (n != 1) {
        n = (n % 2 == 0) ? n / 2 : 3 * n + 1;
        steps++;
    }
    printf("collatz27=%d\n", steps);
    return 0;
}
