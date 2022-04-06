import subprocess
from typing import List
import unittest

from tc2.codegen import StringGenerator, StdoutGenerator, gen_all
from tc2.parser import Node, Parser, tokenize


class CodeGenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.gen = StringGenerator()

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
            self.assertEqual(exe.returncode, exit_code)
        else:
            self.fail('failed to link generated assembly')

    def test_main_0(self):
        asm = self.compile('int main() { return 42;}')
        self.assertExitCode(asm, 42)
