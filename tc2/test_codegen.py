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
        os.remove('tmp')
        os.remove('tmp.s')

    def parse(self, source: str) -> List[Node]:
        tokens = tokenize(source)
        parser = Parser(tokens)
        return parser.program()

    def compile(self, source: str) -> str:
        nodes = self.parse(source)
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
