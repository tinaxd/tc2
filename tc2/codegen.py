import os
from typing import List
from .parser import GenNode, ICodeGenerator, Node


class StdoutGenerator(ICodeGenerator):
    def asm(self, asm: str) -> None:
        print(asm)


class StringGenerator(ICodeGenerator):
    def __init__(self) -> None:
        super().__init__()
        self.buf = []

    def asm(self, asm: str) -> None:
        self.buf.append(asm)

    def as_str(self) -> str:
        return os.linesep.join(self.buf)


def gen_all(gen: ICodeGenerator, nodes: List[GenNode]) -> None:
    gen.asm('.intel_syntax noprefix')
    gen.asm('.globl main')
    for node in nodes:
        node.gen(gen)
        gen.asm('mov rsp, rbp')
        gen.asm('pop rbp')
        gen.asm('ret')
    gen.asm('')
