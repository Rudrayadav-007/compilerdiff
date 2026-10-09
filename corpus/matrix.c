#include <stdio.h>

#define N 3

int main(void) {
    int a[N][N] = {{1, 2, 3}, {4, 5, 6}, {7, 8, 9}};
    int b[N][N] = {{9, 8, 7}, {6, 5, 4}, {3, 2, 1}};
    int c[N][N];
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++) {
            c[i][j] = 0;
            for (int k = 0; k < N; k++) c[i][j] += a[i][k] * b[k][j];
        }
    for (int i = 0; i < N; i++) printf("%d %d %d\n", c[i][0], c[i][1], c[i][2]);
    printf("trace=%d\n", c[0][0] + c[1][1] + c[2][2]);
    return 0;
}
