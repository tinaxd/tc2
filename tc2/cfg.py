from typing import TYPE_CHECKING, List, Tuple


from tc2.parser import BinaryNode, BlockNode, ForNode, IfNode, NodeKind, ReturnNode

if TYPE_CHECKING:
    from .parser import DefNode, Node


class CFGNode:
    def __init__(self, node: 'Node') -> None:
        self.node = node


class CFGNodeReturn(CFGNode):
    def __init__(self) -> None:
        super().__init__(None)


class CFG:
    def __init__(self, func: 'DefNode') -> None:
        self.func = func
        self.nodes: List[CFGNode] = []
        self.edges: List[List[int]] = []

    def _append_block(self, block: CFGNode) -> int:
        self.nodes.append(block)
        self.edges.append([])
        return len(self.nodes)-1

    def _connect(self, fromid: int, toid: int) -> None:
        self.edges[fromid].append(toid)

    def analyze(self) -> None:
        lastidx = []
        for stmt in self.func.body.stmts:
            lasts = self._analyze_stmt(stmt, lastidx)
            lastidx = lasts

    def _analyze_stmt(self, node: 'Node', prev: List[int]) -> Tuple[List[int], int]:
        last_indices = []
        start_idx = None
        if isinstance(node, ForNode):
            init_idx = self._analyze_stmt(node.init, prev)
            cond_idx = self._analyze_stmt(node.cond, [init_idx])
            body_idx = self._analyze_stmt()
            step_idx = self._append_block(step_block)

            for id in prev:
                self._connect(id, init_idx)
            self._connect(init_idx, cond_idx)
            last_indices.append(cond_idx)
            body_end_indices = self._analyze_stmt(node.body, [cond_idx])
            for end in body_end_indices:
                self._connect(end, step_idx)
            self._connect(step_idx, cond_idx)
        elif isinstance(node, IfNode):
            cond_idx = self._analyze_stmt(node.cond, prev)
            then_idx = self._analyze_stmt(node.then, cond_idx)

            for id in then_idx:
                last_indices.append(id)

            if node.els is not None:
                else_idx = self._analyze_stmt(node.els, cond_idx)
                for id in else_idx:
                    last_indices.append(id)
            else:
                for id in cond_idx:
                    last_indices.append(id)
        elif isinstance(node, BlockNode):
            lastidx = prev
            for node in node.stmts:
                lasts = self._analyze_stmt(node, lastidx)
                lastidx = lasts
            for id in lastidx:
                last_indices.append(id)
        elif isinstance(node, ReturnNode):
            eval_idx = self._analyze_stmt(node.val, prev)
            return_cfg = CFGNodeReturn()
            return_idx = self._append_block(return_cfg)
            for id in eval_idx:
                self._connect(id, return_idx)
        elif isinstance(node, BinaryNode) and node.kind == NodeKind.ASSIGN:
            rhs_idx = self._analyze_stmt(node.rhs, prev)
            lhs_idx = self._analyze_stmt(node.lhs, rhs_idx)
            for id in lhs_idx:
                last_indices.append(id)
        else:
            block = CFGNode(node)
            blockidx = self._append_block(block)
            for lastidx in prev:
                if lastidx != -1:
                    self._connect(lastidx, blockidx)
            last_indices.append(blockidx)

        return last_indices

    def make_dot(self) -> str:
        lines = []
        lines.append('digraph CFG {')
        for i, node in enumerate(self.nodes):
            name = f'block{i}'
            label = f'{node.node}'
            lines.append(f'{name} [')
            lines.append(f'label={label}')
            lines.append(']')

        for fromid, edges in enumerate(self.edges):
            for toid in edges:
                fromname = f'block{fromid}'
                toname = f'block{toid}'
                lines.append(f'{fromname} -> {toname}')

        lines.append('}')

        return "\n".join(lines)


if __name__ == '__main__':
    import sys
    from .parser import tokenize, Parser
    # from .codegen import StdoutGenerator, gen_all
    source = sys.argv[1]
    tokens = tokenize(source)
    parser = Parser(tokens)

    nodes = parser.program()
    lvars = parser.get_local_vars()

    cfg = CFG(nodes[0])
    cfg.analyze()
    print(cfg.make_dot())
