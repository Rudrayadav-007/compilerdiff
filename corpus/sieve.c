#include <stdio.h>

#define LIMIT 100

int main(void) {
    int composite[LIMIT + 1] = {0};
    int count = 0, sum = 0, largest = 0;
    for (int i = 2; i <= LIMIT; i++) {
        if (composite[i]) continue;
        count++;
        sum += i;
        largest = i;
        for (int j = i * i; j <= LIMIT; j += i) composite[j] = 1;
    }
    printf("count=%d\nsum=%d\nlargest=%d\n", count, sum, largest);
    return 0;
}
