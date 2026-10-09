#include <stdio.h>

static const char *classify(int x) {
    if (x < 0) return "negative";
    else if (x == 0) return "zero";
    return "positive";
}

int main(void) {
    int samples[3] = {-5, 0, 7};
    for (int i = 0; i < 3; i++) printf("%d %s\n", samples[i], classify(samples[i]));
    for (int i = 1; i <= 15; i++) {
        if (i % 15 == 0) printf("FizzBuzz\n");
        else if (i % 3 == 0) printf("Fizz\n");
        else if (i % 5 == 0) printf("Buzz\n");
        else printf("%d\n", i);
    }
    return 0;
}
