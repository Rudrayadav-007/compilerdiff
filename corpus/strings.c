#include <stdio.h>

static int length(const char *s) {
    int n = 0;
    while (s[n] != '\0') n++;
    return n;
}

static void reverse(char *s) {
    int i = 0, j = length(s) - 1;
    while (i < j) {
        char t = s[i];
        s[i++] = s[j];
        s[j--] = t;
    }
}

static int is_palindrome(const char *s) {
    for (int i = 0, j = length(s) - 1; i < j; i++, j--)
        if (s[i] != s[j]) return 0;
    return 1;
}

int main(void) {
    char text[] = "Hello, World";
    int vowels = 0;
    for (int i = 0; text[i] != '\0'; i++) {
        char ch = text[i];
        if (ch == 'a' || ch == 'e' || ch == 'i' || ch == 'o' || ch == 'u') vowels++;
    }
    printf("length=%d\nvowels=%d\n", length(text), vowels);
    reverse(text);
    printf("reversed=%s\n", text);
    printf("racecar_palindrome=%d\n", is_palindrome("racecar"));
    printf("hello_palindrome=%d\n", is_palindrome("hello"));
    return 0;
}
