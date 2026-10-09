#include <stdio.h>

int main(void) {
    printf("exiting with 3\n");
    fprintf(stderr, "note: deliberate nonzero exit\n");
    return 3;
}
