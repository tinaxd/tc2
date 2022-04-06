import os
from typing import Dict, List, Optional
from .parser import GenNode, ICodeGenerator, LVarPlacement, LocalVar, Node, StackLayout


class StdoutGenerator(ICodeGenerator):
    def asm(self, asm: str) -> None:
        print(asm)


class StringGenerator(ICodeGenerator):
    def __init__(self, lvars: Dict[str, List[LocalVar]] = None) -> None:
        super().__init__()
        self.buf = []
        self.lvars = lvars
        self.current_function = ""
        self.label_num = 0

    def update_lvars(self, lvars: Dict[str, List[LocalVar]]) -> None:
        self.lvars = lvars

    def get_rsp_sub(self, func: str) -> int:
        layout = self.get_stack_layout(func)
        if not layout.lvars:
            return 0
        return max([v.offset for v in layout.lvars])

    def get_stack_layout(self, func: str) -> StackLayout:
        vars = self.lvars[func]
        offset = 0
        places = []
        for var in vars:
            offset += 4
            place = LVarPlacement(var.name, offset, 4)
            places.append(place)
        return StackLayout(places)

    def get_offset(self, varname: str) -> Optional[int]:
        layout = self.get_stack_layout(self.current_function)
        for var in layout.lvars:
            if var.name == varname:
                return var.offset
        return None

    def update_current_function(self, func: str) -> None:
        self.current_function = func

    def asm(self, asm: str) -> None:
        self.buf.append(asm)

    def as_str(self) -> str:
        return os.linesep.join(self.buf)

    def generate_label(self) -> str:
        s = f'.L{self.label_num}'
        self.label_num += 1
        return s


def gen_all(gen: ICodeGenerator, nodes: List[GenNode]) -> None:
    gen.asm('.intel_syntax noprefix')
    gen.asm('.globl main')
    for node in nodes:
        node.gen(gen)
        gen.asm('mov rsp, rbp')
        gen.asm('pop rbp')
        gen.asm('ret')
    gen.asm('')
