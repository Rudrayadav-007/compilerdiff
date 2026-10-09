#include <stdio.h>

int main(void) {
    int a = 17, b = 5;
    printf("add=%d\n", a + b);
    printf("sub=%d\n", a - b);
    printf("mul=%d\n", a * b);
    printf("div=%d\n", a / b);
    printf("mod=%d\n", a % b);
    printf("neg_div=%d\n", -17 / 5);
    printf("neg_mod=%d\n", -17 % 5);
    printf("shift=%d\n", 1 << 10);
    printf("bits=%d\n", (0xF0 & 0x3C) | 0x01);
    return 0;
}
