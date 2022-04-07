#include <stdio.h>
#include <stdlib.h>

int foo() {
    printf("foo OK!\n");
    return 11;
}

int bar(int a, int b) {
    printf("bar %d+%d=%d OK!\n", a, b, a+b);
    return 12;
}

int foobar(int a) {
    printf("foobar a=%d OK!\n", a);
    return 13;
}

void alloc4(int **p, int a, int b, int c, int d) {
    *p = malloc(sizeof(int) * 4);
    int *q = *p;
    q[0] = a;
    q[1] = b;
    q[2] = c;
    q[3] = d;
}
