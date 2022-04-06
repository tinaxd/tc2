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

    def assertExitCode(self, asm: str, exit_code: int) -> None:
        with open('tmp.s', 'w') as f:
            f.write(asm)
        proc = subprocess.run(['cc', '-o', 'tmp', 'tmp.s'])
        if proc.returncode == 0:
            exe = subprocess.run(['./tmp'])
            self.assertEqual(exe.returncode, exit_code, msg=asm)
        else:
            self.fail('failed to link generated assembly')

    def assertCompileExitCode(self, source: str, exit_code: int) -> None:
        asm = self.compile(source)
        self.assertExitCode(asm, exit_code)

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
        self.assertCompileExitCode('int main(){if(1) return 2; return 3;}', 3)
    
    def test_if1_then(self):
        self.assertCompileExitCode('int main(){if(1) return 2; else return 3;}', 2)

    def test_if0_else(self):
        self.assertCompileExitCode('int main(){if(0) return 2; else return 3;}', 3)
    
    def test_while1(self):
        self.assertCompileExitCode('int main(){while(1) return 3; return 2;}', 3)
    
    def test_while0(self):
        self.assertCompileExitCode('int main(){while(0) return 3; return 2;}', 2)

    def test_if1(self):
        self.assertCompileExitCode("int main() {int i; for(i=0; i<6; i=i+1) i=i; 4;}",4)

    def test_if2(self):
        self.assertCompileExitCode("int main() {int i; for(i=0; i<6; i=i+1) if(i == 3) return i; 4;}", 3)
    
    def test_if3(self):
        self.assertCompileExitCode("int main() {int i; for(i=0; i<6; i=i+1) if(i==5) return 100; i;}", 100)

    def test_if4(self):
        self.assertCompileExitCode("int main() {int i; for(i=0; i<6; i=i+1) if(i==6) return 100; 7;}",7)

    def test_if5(self):
        self.assertCompileExitCode("int main() {int i; for(i=0; i<6; ) if((i=i+1) == 3) return i; 4;}",3)

    def test_if6(self):
        self.assertCompileExitCode("int main() {for(;;) return 100; return 50;}",100)
