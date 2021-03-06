import os
from typing import Dict, List, Optional, TYPE_CHECKING
from .parser import GenNode, ICodeGenerator, LVarPlacement, LocalVar, Node, StackLayout, TypeKind

if TYPE_CHECKING:
    from .parser import Type


class StringGenerator(ICodeGenerator):
    def __init__(self, lvars: Dict[str, List[LocalVar]] = None) -> None:
        super().__init__()
        self.buf = []
        self.lvars = lvars
        self.current_function = ""
        self.label_num = 0

    def _get_type_size(self, ty: 'Type') -> int:
        if ty.kind == TypeKind.PTR:
            return 8
        elif ty.kind == TypeKind.INT:
            return 4
        elif ty.kind == TypeKind.ARRAY:
            return ty.array_size * self._get_type_size(ty.ptr_to)
        elif ty.kind == TypeKind.CHAR:
            return 1
        else:
            raise NotImplementedError()

    def _get_alignment(self, ty: 'Type') -> int:
        if ty.kind == TypeKind.PTR:
            return 8
        elif ty.kind == TypeKind.INT:
            return 4
        elif ty.kind == TypeKind.ARRAY:
            return self._get_alignment(ty.ptr_to)
        elif ty.kind == TypeKind.CHAR:
            return 1
        else:
            raise NotImplementedError()

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
            size = self._get_type_size(var.ty)
            mod = self._get_alignment(var.ty)
            offset += size
            if offset % mod != 0:
                padding = mod - (offset % mod)
                offset += padding
            place = LVarPlacement(var.name, offset, size)
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


class StdoutGenerator(StringGenerator):
    def asm(self, asm: str) -> None:
        print(asm)


def gen_all(gen: ICodeGenerator, nodes: List[GenNode]) -> None:
    gen.asm('.intel_syntax noprefix')
    gen.asm('.globl main')
    for node in nodes:
        node.gen(gen)
        gen.asm('mov rsp, rbp')
        gen.asm('pop rbp')
        gen.asm('ret')
    gen.asm('')


if __name__ == '__main__':
    import sys
    from .parser import tokenize, Parser
    source = sys.argv[1]
    tokens = tokenize(source)
    parser = Parser(tokens)

    nodes = parser.program()
    lvars = parser.get_local_vars()

    compiler = StdoutGenerator(lvars)
    gen_all(compiler, nodes)
