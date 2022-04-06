from dataclasses import dataclass
from shutil import ExecError
from typing import Dict, List, Optional
from enum import Enum
from abc import ABCMeta, abstractmethod

import sys


def error_at(tokstr: str, msg: str) -> None:
    print(tokstr, msg)
    sys.exit(1)


class TokenKind(Enum):
    RESERVED = 1
    IDENT = 2
    NUM = 3
    RETURN = 4
    IF = 5
    ELSE = 6
    WHILE = 7
    FOR = 8
    EOF = 9


class Token:
    def __init__(self, kind: TokenKind, string: str, val=None) -> None:
        self.kind = kind
        self.string = string
        self.val = val

    def __eq__(self, o) -> bool:
        if isinstance(o, Token):
            return self.kind == o.kind and self.string == o.string and self.val == o.val
        return False

    def __str__(self) -> str:
        return f'<Token {self.kind} {self.string}>'

    def __repr__(self) -> str:
        return f'Token({repr(self.kind)}, {repr(self.string)}, {repr(self.val)})'


class TokenizeError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class NodeKind(Enum):
    ADD = 1
    SUB = 2
    MUL = 3
    DIV = 4
    LT = 5
    LE = 6
    EQ = 7
    NEQ = 8
    ASSIGN = 9
    NUM = 10
    RETURN = 11
    IF = 12
    WHILE = 13
    FOR = 14
    BLOCK = 15
    CALL = 16
    DEF = 17
    DEREF = 18
    ADDR = 19
    EMPTY = 20
    LVAR = 21


@dataclass
class LVarPlacement:
    name: str
    offset: int
    size: int


@dataclass
class StackLayout:
    lvars: List[LVarPlacement]


class ICodeGenerator(metaclass=ABCMeta):
    @abstractmethod
    def asm(self, asm: str) -> None: ...

    @abstractmethod
    def get_stack_layout(self, func: str) -> StackLayout: ...

    @abstractmethod
    def get_rsp_sub(self, func: str) -> int: ...

    @abstractmethod
    def get_offset(self, varname: str) -> int: ...

    @abstractmethod
    def update_current_function(self, func: str) -> None: ...


class GenError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


class Node(metaclass=ABCMeta):
    def __init__(self, kind: NodeKind) -> None:
        self.kind = kind

    def __str__(self) -> str:
        return f'<Node {self.kind}>'


class GenNode(Node):
    @abstractmethod
    def gen(self, g: ICodeGenerator) -> None: ...
    @abstractmethod
    def gen_lval(self, g: ICodeGenerator) -> None: ...


class ReturnNode(GenNode):
    def __init__(self, val: Node) -> None:
        super().__init__(NodeKind.RETURN)
        self.val = val

    def gen(self, g: ICodeGenerator) -> None:
        self.val.gen(g)
        g.asm("pop rax")
        g.asm("mov rsp, rbp")
        g.asm("pop rbp")
        g.asm("ret")

    def gen_lval(self, g: ICodeGenerator) -> None:
        raise NotImplementedError()


class EmptyNode(GenNode):
    def __init__(self) -> None:
        super().__init__(NodeKind.EMPTY)

    def gen(self, g: ICodeGenerator) -> None:
        pass

    def gen_lval(self, g: ICodeGenerator) -> None:
        pass


class UnaryNode(GenNode):
    def __init__(self, kind: NodeKind, node: Node) -> None:
        super().__init__(kind)
        self.node = node

    def gen(self, g: ICodeGenerator) -> None:
        raise NotImplementedError()

    def gen_lval(self, g: ICodeGenerator) -> None:
        raise NotImplementedError()


class BinaryNode(GenNode):
    def __init__(self, kind: NodeKind, lhs: GenNode, rhs: GenNode) -> None:
        super().__init__(kind)
        self.lhs = lhs
        self.rhs = rhs

    def gen(self, g: ICodeGenerator) -> None:
        if self.kind == NodeKind.ASSIGN:
            self.lhs.gen_lval(g)
            self.rhs.gen(g)

            g.asm('pop rdi')
            g.asm('pop rax')
            g.asm('mov DWORD PTR [rax], edi')
            g.asm('push rdi')
            return

        self.lhs.gen(g)
        self.rhs.gen(g)
        g.asm('pop rdi')
        g.asm('pop rax')
        if self.kind == NodeKind.ADD:
            g.asm('add rax, rdi')
        elif self.kind == NodeKind.SUB:
            g.asm('sub rax, rdi')
        elif self.kind == NodeKind.MUL:
            g.asm('imul rax, rdi')
        elif self.kind == NodeKind.DIV:
            g.asm('cqo')
            g.asm('idiv rdi')
        elif self.kind == NodeKind.LT:
            g.asm('cmp rax, rdi')
            g.asm('setl al')
            g.asm('movzb rax, al')
        elif self.kind == NodeKind.LE:
            g.asm('cmp rax, rdi')
            g.asm('setle al')
            g.asm('movzb rax, al')
            g.asm('cmp rax, rdi')
            g.asm('sete al')
            g.asm('movzb rax, al')
        elif self.kind == NodeKind.EQ:
            g.asm('cmp rax, rdi')
            g.asm('sete al')
            g.asm('movzb rax, al')
        elif self.kind == NodeKind.NEQ:
            g.asm('cmp rax, rdi')
            g.asm('setne al')
            g.asm('movzb rax, al')
        else:
            raise NotImplementedError(f'Kind: {self.kind}')
        g.asm('push rax')

    def gen_lval(self, g: ICodeGenerator) -> None:
        raise NotImplementedError()


class NumNode(GenNode):
    def __init__(self, val: int) -> None:
        super().__init__(NodeKind.NUM)
        self.val = val

    def gen(self, g: ICodeGenerator) -> None:
        g.asm(f"push {self.val}")

    def gen_lval(self, g: ICodeGenerator) -> None:
        raise NotImplementedError()


class LVarNode(GenNode):
    def __init__(self, lvar: 'LocalVar') -> None:
        super().__init__(NodeKind.LVAR)
        self.lvar = lvar

    def gen(self, g: ICodeGenerator) -> None:
        self.gen_lval(g)
        g.asm('pop rax')
        g.asm('mov eax, DWORD PTR [rax]')
        g.asm('push rax')

    def gen_lval(self, g: ICodeGenerator) -> None:
        g.asm('mov rax, rbp')
        offset = g.get_offset(self.lvar.name)
        g.asm(f'sub rax, {offset}')
        g.asm('push rax')


class BlockNode(GenNode):
    def __init__(self) -> None:
        super().__init__(NodeKind.BLOCK)
        self.stmts: List[Node] = []

    def append(self, stmt: Node) -> None:
        self.stmts.append(stmt)

    def gen(self, g: ICodeGenerator) -> None:
        for stmt in self.stmts:
            if isinstance(stmt, GenNode):
                stmt.gen(g)
            else:
                raise GenError(f"Non GenNode in BlockNode: {stmt}")

    def gen_lval(self, g: ICodeGenerator) -> None:
        raise NotImplementedError()


class DefNode(GenNode):
    def __init__(self, funcname: str, body: BlockNode) -> None:
        super().__init__(NodeKind.DEF)
        self.funcname = funcname
        self.body = body

    def gen(self, g: ICodeGenerator) -> None:
        g.update_current_function(self.funcname)
        g.asm(f'{self.funcname}:')
        g.asm('push rbp')
        g.asm('mov rbp, rsp')

        offset = g.get_rsp_sub(self.funcname)
        g.asm(f'sub rsp, {offset}')

        # TODO: push arguments

        self.body.gen(g)
        g.asm('pop rax')

    def gen_lval(self, g: ICodeGenerator) -> None:
        raise NotImplementedError()


def substr(s: str, start: int, count: int) -> str:
    return s[start:start+count]


def tokenize(s: str) -> List[Token]:
    p = 0
    tokens = []

    def new_token(tok: Token) -> None:
        tokens.append(tok)
    while p < len(s):
        ch = s[p]

        if ch.isspace():
            p += 1
            continue

        chch = substr(s, p, 2)
        if chch == '==' or chch == '<=' or chch == '>=' or chch == '!=':
            new_token(Token(TokenKind.RESERVED, chch))
            p += 2
            continue

        if ch in ['<', '>', '+', '-', '*', '/', '(', ')', '=', ';', '{', '}', ',', '&', '[', ']']:
            new_token(Token(TokenKind.RESERVED, ch))
            p += 1
            continue

        if substr(s, p, 6) == 'return':
            new_token(Token(TokenKind.RETURN, substr(s, p, 6)))
            p += 6
            continue

        def keyword(key: str) -> bool:
            return substr(s, p, len(key)) == key and not s[p+len(key)].isalnum()

        if keyword('return'):
            new_token(Token(TokenKind.RETURN, substr(s, p, 6)))
            p += 6
            continue

        if keyword('if'):
            new_token(Token(TokenKind.IF, substr(s, p, 2)))
            p += 2
            continue

        if keyword('else'):
            new_token(Token(TokenKind.ELSE, substr(s, p, 4)))
            p += 4
            continue

        if keyword('while'):
            new_token(Token(TokenKind.WHILE, substr(s, p, 5)))
            p += 5
            continue

        if keyword('for'):
            new_token(Token(TokenKind.FOR, substr(s, p, 3)))
            p += 3
            continue

        if keyword('sizeof'):
            new_token(Token(TokenKind.RESERVED, substr(s, p, 6)))
            p += 6
            continue

        if keyword('int'):
            new_token(Token(TokenKind.RESERVED, substr(s, p, 3))
                      )
            p += 3
            continue

        # integer
        if ch.isdigit():
            fch = ch
            valstr = []
            while fch.isdigit():
                valstr.append(fch)
                p += 1
                if p >= len(s):
                    break
                fch = s[p]
            sub = "".join(valstr)
            val = int(sub)
            new_token(Token(TokenKind.NUM, sub, val))
            continue

        # LVar
        lvar_lst = []
        fch = ch
        i = 0
        while (i == 0 and 'A' <= fch <= 'z') or (i != 0 and fch.isalnum()):
            lvar_lst.append(fch)
            p += 1
            i += 1
            fch = s[p]
        name = "".join(lvar_lst)
        if i != 0:
            new_token(Token(TokenKind.IDENT, name))
            continue

        err = s[:p] + "^" + s[p:]
        raise TokenizeError(f'cannot tokenize: {err}')

    new_token(Token(TokenKind.EOF, ""))
    return tokens


class LocalVar:
    def __init__(self, name: str) -> None:
        self.name = name


class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.p = 0
        self.current_function = ""
        self.local_vars: Dict[str, List[LocalVar]] = {}

    @property
    def current(self) -> Token:
        return self.tokens[self.p]

    def get_local_vars(self):
        return self.local_vars

    def find_local_var_in_func(self, name: str) -> Optional[LocalVar]:
        vars = self.local_vars[self.current_function]
        for var in vars:
            if var.name == name:
                return var
        return None

    def consume(self, op: str) -> bool:
        token = self.current
        if token.kind != TokenKind.RESERVED or token.string != op:
            return False
        self.p += 1
        return True

    def consume_kind(self, kind: TokenKind) -> bool:
        token = self.current
        if token.kind != kind:
            return False
        self.p += 1
        return True

    def consume_number(self) -> Optional[int]:
        if self.current.kind != TokenKind.NUM:
            return None
        val = self.current.val
        self.p += 1
        return val

    def expect(self, op: str) -> None:
        token = self.current
        if token.kind != TokenKind.RESERVED or token.string != op:
            error_at(token.string, f"not {op}")
        self.p += 1

    def expect_ident(self) -> Token:
        if self.current.kind != TokenKind.IDENT:
            error_at(self.current.string,
                     f"not an ident {self.current.string}")
        val = self.current
        self.p += 1
        return val

    def register_local_var(self, name: str) -> None:
        vars_in_func = self.local_vars[self.current_function]
        vars_in_func.append(LocalVar(name))

    def program(self) -> List[Node]:
        code = []
        while self.current.kind != TokenKind.EOF:
            code.append(self.definition())
        return code

    def definition(self) -> Node:
        self.expect("int")
        ident = self.expect_ident()
        self.current_function = ident.string
        self.local_vars[ident.string] = []
        self.expect("(")
        params = []
        if not self.consume(")"):
            # params exist
            self.expect("int")
            id = self.expect_ident()
            params.append(id)
            while True:
                if self.consume(","):
                    self.expect("int")
                    id1 = self.expect_ident()
                    params.append(id1)
                else:
                    break
            self.expect(")")

        # TODO: register params as lvars

        self.consume("{")
        body = BlockNode()
        while True:
            if self.consume("}"):
                break
            body.append(self.stmt())

        node = DefNode(ident.string, body)
        return node

    def stmt(self) -> Node:
        if self.consume_kind(TokenKind.RETURN):
            node = self.expr()
            self.expect(";")
            return ReturnNode(node)
        elif self.consume("int"):
            stars = 0
            while self.consume("*"):
                stars += 1
            tok = self.expect_ident()

            # array check
            array_size = 0
            is_array = False
            if self.consume("["):
                is_array = True
                raise NotImplementedError()

            self.expect(";")

            # type construction
            # TODO:
            self.register_local_var(tok.string)
            return EmptyNode()
        else:
            node = self.expr()
            self.expect(";")
            return node

    def expr(self) -> Node:
        return self.assign()

    def assign(self) -> Node:
        node = self.equality()
        if self.consume("="):
            node = BinaryNode(NodeKind.ASSIGN, node, self.assign())
        return node

    def equality(self) -> Node:
        node = self.relational()
        while True:
            if self.consume("=="):
                node = BinaryNode(NodeKind.EQ, node, self.relational())
            elif self.consume("!="):
                node = BinaryNode(NodeKind.NEQ, node, self.relational())
            else:
                break
        return node

    def relational(self) -> Node:
        node = self.add()
        while True:
            if self.consume("<"):
                node = BinaryNode(NodeKind.LT, node, self.add())
            elif self.consume("<="):
                node = BinaryNode(NodeKind.LE, node, self.add())
            elif self.consume(">"):
                node = BinaryNode(NodeKind.LT, self.add(), node)
            elif self.consume(">="):
                node = BinaryNode(NodeKind.LE, self.add(), node)
            elif self.consume("=="):
                node = BinaryNode(NodeKind.EQ, node, self.add())
            elif self.consume("!="):
                node = BinaryNode(NodeKind.NEQ, node, self.add())
            else:
                break
        return node

    def add(self) -> Node:
        node = self.mul()
        while True:
            if self.consume("+"):
                m = self.mul()
                node = BinaryNode(NodeKind.ADD, node, m)
            elif self.consume("-"):
                m = self.mul()
                node = BinaryNode(NodeKind.SUB, node, m)
            else:
                break
        return node

    def mul(self) -> Node:
        node = self.unary()
        while True:
            if self.consume("*"):
                node = BinaryNode(NodeKind.MUL, node, self.unary())
            elif self.consume("/"):
                node = BinaryNode(NodeKind.DIV, node, self.unary())
            else:
                break
        return node

    def unary(self) -> Node:
        if self.consume("+"):
            return self.subscript()
        if self.consume("-"):
            p = self.subscript()
            return BinaryNode(NodeKind.SUB, NumNode(0), p)
        if self.consume("*"):
            return UnaryNode(NodeKind.DEREF, self.unary())
        if self.consume("&"):
            return UnaryNode(NodeKind.ADDR, self.unary())
        if self.consume("sizeof"):
            raise NotImplementedError()
        return self.subscript()

    def subscript(self) -> Node:
        p = self.primary()
        if self.consume("["):
            index = self.expr()
            self.expect("]")
            add = BinaryNode(NodeKind.ADD, p, index)
            deref = UnaryNode(NodeKind.DEREF, add)
            return deref
        return p

    def primary(self) -> Node:
        # paren expr
        if self.consume("("):
            node = self.expr()
            self.expect(")")
            return node

        # integer literal
        num = self.consume_number()
        if num is not None:
            return NumNode(num)

        ident = self.expect_ident()
        if self.consume("("):
            # function call
            raise NotImplementedError()
        else:
            # local variable
            lvar = self.find_local_var_in_func(ident.string)
            return LVarNode(lvar)
