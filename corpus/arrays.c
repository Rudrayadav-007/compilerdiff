#include <stdio.h>

#define N 8

int main(void) {
    int a[N] = {5, 3, 8, 1, 9, 2, 7, 4};
    int sum = 0, max = a[0];
    for (int i = 0; i < N; i++) {
        sum += a[i];
        if (a[i] > max) max = a[i];
    }
    for (int i = 0; i < N - 1; i++)
        for (int j = 0; j < N - 1 - i; j++)
            if (a[j] > a[j + 1]) {
                int t = a[j];
                a[j] = a[j + 1];
                a[j + 1] = t;
            }
    printf("sorted:");
    for (int i = 0; i < N; i++) printf(" %d", a[i]);
    printf("\nsum=%d\nmax=%d\n", sum, max);
    return 0;
}
