import os
import subprocess
from typing import List
import unittest

from tc2.codegen import StringGenerator, StdoutGenerator, gen_all
from tc2.parser import Node, Parser, tokenize


class CodeGenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.gen = StringGenerator()

    def tearDown(self) -> None:
        def rem(filename):
            try:
                os.remove(filename)
            except FileNotFoundError:
                pass
        rem('tmp')
        rem('tmp.s')

    def parse(self, source: str):
        tokens = tokenize(source)
        parser = Parser(tokens)
        return parser.program(), parser.get_local_vars()

    def compile(self, source: str) -> str:
        nodes, lvars = self.parse(source)
        self.gen.update_lvars(lvars)
        gen_all(self.gen, nodes)
        return self.gen.as_str()

    def assertExitCode(self, asm: str, exit_code: int, libraries: List[str] = []) -> None:
        with open('tmp.s', 'w') as f:
            f.write(asm)
        cmd = ['cc', '-o', 'tmp', 'tmp.s']
        for lib in libraries:
            cmd.append(f'{lib}.o')
        proc = subprocess.run(cmd)
        if proc.returncode == 0:
            exe = subprocess.run(['./tmp'])
            self.assertEqual(exe.returncode, exit_code, msg=asm)
        else:
            self.fail(f'failed to link generated assembly, asm: {asm}')

    def assertCompileExitCode(self, source: str, exit_code: int, libraries: List[str] = []) -> None:
        asm = self.compile(source)
        self.assertExitCode(asm, exit_code, libraries=libraries)

    def test_main_simple(self):
        self.assertCompileExitCode('int main() { return 42;}', 42)

    def test_main_expr(self):
        self.assertCompileExitCode('int main() {return 5+6*7;}', 47)

    def test_main_paren_expr(self):
        self.assertCompileExitCode('int main() {return 5*(9-6);}', 15)

    def test_main_comp_lt(self):
        self.assertCompileExitCode('int main(){return 1<2;}', 1)

    def test_main_comp_gte(self):
        self.assertCompileExitCode('int main(){return 1>=2;}', 0)

    def test_main_var1(self):
        self.assertCompileExitCode('int main(){int a; return a=2;}', 2)

    def test_main_var2(self):
        self.assertCompileExitCode(
            'int main(){int a; int b; return a=b=2;}', 2)

    def test_main_var1_ret(self):
        self.assertCompileExitCode('int main(){int a; a=2; return a;}', 2)

    def test_main_var2_ret_a(self):
        self.assertCompileExitCode(
            'int main(){int a; int b;a=b=2; return a;}', 2)

    def test_main_var2_ret_b(self):
        self.assertCompileExitCode(
            'int main(){int a; int b;a=b=2; return b;}', 2)

    def test_main_var2_ret_one(self):
        self.assertCompileExitCode(
            'int main(){int a; int b;a=2; return a;}', 2)

    def test_if1(self):
        self.assertCompileExitCode('int main(){if(1) return 2;}', 2)

    def test_if1_early(self):
        self.assertCompileExitCode('int main(){if(1) return 2; return 3;}', 2)

    def test_if0(self):
        self.assertCompileExitCode('int main(){if(1) return 2; return 3;}', 2)

    def test_if1_then(self):
        self.assertCompileExitCode(
            'int main(){if(1) return 2; else return 3;}', 2)

    def test_if0_else(self):
        self.assertCompileExitCode(
            'int main(){if(0) return 2; else return 3;}', 3)

    def test_while1(self):
        self.assertCompileExitCode(
            'int main(){while(1) return 3; return 2;}', 3)

    def test_while0(self):
        self.assertCompileExitCode(
            'int main(){while(0) return 3; return 2;}', 2)

    def test_for1(self):
        self.assertCompileExitCode(
            "int main() {int i; for(i=0; i<6; i=i+1) i=i; 4;}", 4)

    def test_for2(self):
        self.assertCompileExitCode(
            "int main() {int i; for(i=0; i<6; i=i+1) if(i == 3) return i; 4;}", 3)

    def test_for3(self):
        self.assertCompileExitCode(
            "int main() {int i; for(i=0; i<6; i=i+1) if(i==5) return 100; i;}", 100)

    def test_for4(self):
        self.assertCompileExitCode(
            "int main() {int i; for(i=0; i<6; i=i+1) if(i==6) return 100; 7;}", 7)

    def test_for5(self):
        self.assertCompileExitCode(
            "int main() {int i; for(i=0; i<6; ) if((i=i+1) == 3) return i; 4;}", 3)

    def test_for6(self):
        self.assertCompileExitCode(
            "int main() {for(;;) return 100; return 50;}", 100)

    def test_for7(self):
        self.assertCompileExitCode(
            "int main() {int i; for(i=0; i<10; i=i+1) { int a; a = i + 3; return a; } return 10;}", 3)

    def test_for7_a(self):
        self.assertCompileExitCode(
            "int main() {int i; for(i=1; i<10; i=i+1) { int a; a = i + 3; return a; } return 10;}", 4)

    def test_for8(self):
        self.assertCompileExitCode(
            "int main() {int sum; int i; sum = 0; for(i=1; i<=5; i=i+1) sum = sum + i; return sum;}", 15)

    def test_for9(self):
        self.assertCompileExitCode(
            "int main() {int sum; int i; sum = 0; i = 1; while (i <= 5) { sum = sum + i; i = i+1; } return sum;}", 15)

    def test_for10(self):
        self.assertCompileExitCode(
            "int main() {int i; int a; for (i=1; i<=10; i=i+1) {a = i+1; return a;}}", 2)

    def test_for10_a(self):
        self.assertCompileExitCode(
            "int main() {int i; int a; for (i=1; i<=10; i=i+1) {a = i+1; return 2;}}", 2)

    def test_for10_b(self):
        self.assertCompileExitCode(
            "int main() {int i; int a; for (i=1; i<=10; i=i+1) {a = i+1; return 2;} return 2;}", 2)

    def test_for10_c(self):
        self.assertCompileExitCode(
            "int main() {int i; int a; for (i=1; i<=10; i=i+1) {return 2;}}", 2)

    def test_for10_d(self):
        self.assertCompileExitCode(
            "int main() {int i; for (i=1; i<=10; i=i+1) {return 2;} return 10;}", 2)

    def test_for10_e(self):
        self.assertCompileExitCode(
            "int main() {int i; for (i=1; i<10; i=i+1) {return 2;} return 10;}", 2)

    def test_for11(self):
        self.assertCompileExitCode(
            "int main() {int i; int a; for (i=1; i<=3; i=i+1) {a = 1; if (a == 2) return a;} return 100;}", 100)

    def test_for12(self):
        self.assertCompileExitCode(
            "int main() {int i; int a; for (i=1; i<=10; i=i+1) {a = i; if (a == 2) return a;} return 100;}", 2)

    def test_for13(self):
        self.assertCompileExitCode(
            "int main() {int i; int a; for (i=1; i<=10; i=i+1) {a = i+1; if (a == 2) return i;} return 100;}", 1)

    def test_for14(self):
        self.assertCompileExitCode(
            "int main() {int i; int a; for(i=0;i<=1;i=i+1) {a=i;} return a;}", 1
        )

    def test_addadd(self):
        self.assertCompileExitCode(
            "int main(){int i;i=0;i=i+1;i=i+1;i=i+1; return i;}", 3)

    def test_ref_deref(self):
        self.assertCompileExitCode(
            "int main(){int a; int *b; int c;a=3; b=&a; c=*b;return c;}", 3)

    def test_ref1(self):
        self.assertCompileExitCode(
            "int main() {int x; int *y; x=3; y=&x; return *y;}", 3)

    def test_ref2(self):
        self.assertCompileExitCode(
            "int main() {int x; int *y; y = &x; *y = 3; return x;}", 3)

    def test_ref3(self):
        self.assertCompileExitCode(
            "int main() {int *p; alloc4(&p, 1, 2, 4, 8); int *q; q = p+2; return *q;}", 4, libraries=['library'])

    def test_ref4(self):
        self.assertCompileExitCode(
            "int main() {int *p; alloc4(&p, 1, 2, 4, 8); int *q; q = p+2; *q; q=q+1; return *q;}", 8, libraries=['library'])

    def test_fundef(self):
        self.assertCompileExitCode(
            "int foo() {return 0;} int main() {return 1;} int bar() {return 2;}", 1)

    def test_fundef1(self):
        self.assertCompileExitCode(
            "int three() {return 3;} int main() {int a; a= three(); return a;}", 3)

    def test_fundef2(self):
        self.assertCompileExitCode(
            "int three() {return 3;} int main() {return three();}", 3)

    def test_fundef3(self):
        self.assertCompileExitCode(
            "int add(int a, int b) {return a+b;} int main() {return add(2, 3);}", 5)

    def test_fundef4(self):
        self.assertCompileExitCode(
            "int three() {return 3;} int two() {return 2;} int main() {return two()+three();}", 5)

    def test_fundef5(self):
        self.assertCompileExitCode(
            "int add(int a, int b) {return a+b;} int main() {return add(2, add(2,1));}", 5)

    def test_fundef6(self):
        self.assertCompileExitCode(
            "int add(int a, int b) {return a+b;} int sub(int c, int d) {return c-d;} int main() {return add(2, sub(5, 2));}", 5)

    def test_fundef7(self):
        self.assertCompileExitCode(
            "int add(int a, int b) {return a+b;} int sub(int a, int b) {return a-b;} int main() {return add(2, sub(5, 2));}", 5)

    def test_fundef_recursive(self):
        self.assertCompileExitCode(
            "int fibo(int x) { if(x==0) return 0; if(x==1) return 1; return fibo(x-1)+fibo(x-2);} int main(){return fibo(10);}", 55)

    def test_array1(self):
        self.assertCompileExitCode("int main() {int a[10]; return 0;}", 0)

    def test_array2(self):
        self.assertCompileExitCode(
            "int main() {int a[1]; *a=2; return *a+1; }", 3)

    def test_array3(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; *a=3; return *a+1; }", 4)

    def test_array4(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; *(a+1)=4; return *(a+1)+1; }", 5)

    def test_array5(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; *(a+1)=4; *a=3; return *(a+1)+1; }", 5)

    def test_array6(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; *a=4; *(a+1)=3; return (*a)+1; }", 5)

    def test_array7(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; *a=1; *(a+1)=2; return *a + *(a+1); }", 3)

    def test_array8(self):
        self.assertCompileExitCode(
            "int main() {int a[10]; int i; for(i=0; i<10; i=i+1) {*(a+i)=i;} return 0;}", 0)

    def test_array9(self):
        self.assertCompileExitCode(
            "int main() {int a[10]; int i; for(i=0; i<10; i=i+1) {*(a+i)=i;} int sum; sum=0;for(i=0; i<10; i=i+1) sum = sum+ (*(a+i)); return sum;}", 45)

    def test_array10(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; a[1]=4; return a[1]+1; }", 5)

    def test_array11(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; a[0]=4; a[1]=3; return a[0]+1; }", 5)

    def test_array12(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; a[0]=1; a[1]=2; return a[0] + a[1]; }", 3)

    def test_array13(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; *(1+a)=4; return *(1+a)+1; }", 5)

    def test_array14(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; *(1+a)=4; *a=3; return *(1+a)+1; }", 5)

    def test_array15(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; *a=4; *(1+a)=3; return (*a)+1; }", 5)

    def test_array16(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; *a=1; *(1+a)=2; return *a + *(1+a); }", 3)

    def test_array17(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; 1[a]=4; return 1[a]+1; }", 5)

    def test_array18(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; 1[a]=4; 0[a]=3; return 1[a]+1; }", 5)

    def test_array19(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; 0[a]=4; 1[a]=3; return 0[a]+1; }", 5)

    def test_array20(self):
        self.assertCompileExitCode(
            "int main() {int a[2]; 0[a]=1; 1[a]=2; return 0[a] + 1[a]; }", 3)

    def test_char_decl(self):
        self.assertCompileExitCode("int main(){char i; return 3;}", 3)

    def test_char_array_decl(self):
        self.assertCompileExitCode("int main(){char i[100]; return 3;}", 3)

    def test_char_ptr_decl(self):
        self.assertCompileExitCode("int main(){char *i; return 3;}", 3)

    def test_char_ret(self):
        self.assertCompileExitCode("int main(){char a;a=4;return a;}", 4)

    def test_char_add(self):
        self.assertCompileExitCode(
            "int main(){char a; char b;a=2;b=3;int c;c=a+b;return c;}", 5)
