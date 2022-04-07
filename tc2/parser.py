from ctypes import cast
from dataclasses import dataclass
from shutil import ExecError
from typing import Dict, List, NoReturn, Optional
from enum import Enum
from abc import ABCMeta, abstractmethod

import sys


class ParserError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


def error_at(tokstr: str, msg: str) -> NoReturn:
    raise ParserError(f'{tokstr} {msg}')


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

    @abstractmethod
    def generate_label(self) -> str: ...


class GenError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


class TypeKind(Enum):
    INT = 1
    PTR = 2
    ARRAY = 3


class Type:
    def __init__(self, kind: TypeKind, ptr_to: 'Type' = None, array_size: int = 0) -> None:
        self.kind = kind
        self.ptr_to = ptr_to
        self.array_size = array_size

    def __eq__(self, o) -> bool:
        if isinstance(o, Type):
            return self.kind == o.kind and self.ptr_to == o.ptr_to and self.array_size == o.array_size
        return False


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


class TypedNode(GenNode):
    @abstractmethod
    def get_type(self) -> Type: ...


class NodeTypeError(Exception):
    def __init__(self, msg) -> None:
        super().__init__(msg)


class ReturnNode(GenNode):
    def __init__(self, val: GenNode) -> None:
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


class UnaryNode(TypedNode):
    def __init__(self, kind: NodeKind, node: TypedNode) -> None:
        super().__init__(kind)
        self.node = node

    def gen(self, g: ICodeGenerator) -> None:
        if self.kind == NodeKind.ADDR:
            self.node.gen_lval(g)
        elif self.kind == NodeKind.DEREF:
            self.node.gen(g)
            g.asm('pop rax')
            g.asm('mov rax, [rax]')
            g.asm('push rax')
        else:
            raise NotImplementedError()

    def gen_lval(self, g: ICodeGenerator) -> None:
        if self.kind == NodeKind.DEREF:
            self.node.gen(g)
        else:
            raise NotImplementedError()

    def get_type(self) -> Type:
        ty = self.node.get_type()
        if self.kind == NodeKind.DEREF:
            return ty.ptr_to  # type: ignore
        elif self.kind == NodeKind.ADDR:
            return Type(TypeKind.PTR, ty)
        else:
            return ty


class BinaryNode(TypedNode):
    def __init__(self, kind: NodeKind, lhs: TypedNode, rhs: TypedNode) -> None:
        super().__init__(kind)
        self.lhs = lhs
        self.rhs = rhs

    def get_type(self) -> Type:
        # FIXME
        return self.lhs.get_type()

    def gen(self, g: ICodeGenerator) -> None:
        if self.kind == NodeKind.ASSIGN:
            self.lhs.gen_lval(g)
            self.rhs.gen(g)

            g.asm('pop rdi')
            g.asm('pop rax')

            ty = self.lhs.get_type()
            if ty.kind == TypeKind.INT:
                g.asm('mov DWORD PTR [rax], edi')
            elif ty.kind == TypeKind.PTR:
                g.asm('mov QWORD PTR [rax], rdi')
            else:
                raise NotImplementedError()

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


class NumNode(TypedNode):
    def __init__(self, val: int) -> None:
        super().__init__(NodeKind.NUM)
        self.val = val

    def gen(self, g: ICodeGenerator) -> None:
        g.asm(f"push {self.val}")

    def gen_lval(self, g: ICodeGenerator) -> None:
        raise NotImplementedError()

    def get_type(self) -> Type:
        return Type(TypeKind.INT)


class LVarNode(TypedNode):
    def __init__(self, lvar: 'LocalVar') -> None:
        super().__init__(NodeKind.LVAR)
        self.lvar = lvar

    def get_type(self) -> Type:
        return self.lvar.ty

    def gen(self, g: ICodeGenerator) -> None:
        self.gen_lval(g)
        g.asm('pop rax')

        ty = self.get_type()
        if ty.kind == TypeKind.INT:
            g.asm('mov eax, DWORD PTR [rax]')
        elif ty.kind == TypeKind.PTR:
            g.asm('mov rax, QWORD PTR [rax]')
        else:
            raise NotImplementedError()

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


class IfNode(GenNode):
    def __init__(self, cond: GenNode, then: GenNode, els: Optional[GenNode] = None) -> None:
        super().__init__(NodeKind.IF)
        self.cond = cond
        self.then = then
        self.els = els

    def gen(self, g: ICodeGenerator) -> None:
        self.cond.gen(g)
        g.asm('pop rax')
        g.asm('cmp rax, 0')
        end_label = g.generate_label()
        if self.els is None:
            # without else clause
            g.asm(f'je {end_label}')
            self.then.gen(g)
            g.asm(f'{end_label}:')
        else:
            # with else clause
            else_label = g.generate_label()
            g.asm(f'je {else_label}')
            self.then.gen(g)
            g.asm(f'jmp {end_label}')
            g.asm(f'{else_label}:')
            self.els.gen(g)
            g.asm(f'{end_label}:')

    def gen_lval(self, g: ICodeGenerator) -> None:
        raise NotImplementedError()


class WhileNode(GenNode):
    def __init__(self, cond: GenNode, body: GenNode) -> None:
        super().__init__(NodeKind.WHILE)
        self.cond = cond
        self.body = body

    def gen(self, g: ICodeGenerator) -> None:
        begin_label = g.generate_label()
        end_label = g.generate_label()
        g.asm(f'{begin_label}:')
        self.cond.gen(g)
        g.asm('pop rax')
        g.asm('cmp rax, 0')
        g.asm(f'je {end_label}')
        self.body.gen(g)
        g.asm(f'jmp {begin_label}')
        g.asm(f'{end_label}:')

    def gen_lval(self, g: ICodeGenerator) -> None:
        raise NotImplementedError()


class ForNode(GenNode):
    def __init__(self, init: Optional[GenNode], cond: Optional[GenNode], step: Optional[GenNode], body: GenNode) -> None:
        super().__init__(NodeKind.FOR)
        self.init = init
        self.cond = cond
        self.step = step
        self.body = body

    def gen(self, g: ICodeGenerator) -> None:
        begin_label = g.generate_label()
        end_label = g.generate_label()
        if self.init is not None:
            self.init.gen(g)
        g.asm(f'{begin_label}:')

        if self.cond is not None:
            self.cond.gen(g)
        else:
            # no cond (always 1)
            g.asm('mov rax, 1')
            g.asm('push rax')
        g.asm('pop rax')
        g.asm('cmp rax, 0')
        g.asm(f'je {end_label}')

        self.body.gen(g)

        if self.step is not None:
            self.step.gen(g)
            g.asm('pop rax')

        g.asm(f'jmp {begin_label}')
        g.asm(f'{end_label}:')

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
    def __init__(self, name: str, ty: Type) -> None:
        self.name = name
        self.ty = ty


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

    def expect_number(self) -> int:
        if self.current.kind != TokenKind.NUM:
            error_at(self.current.string,
                     f'not a number: {self.current.string}')
        val = self.current.val
        self.p += 1
        return val

    def register_local_var(self, name: str, ty: Type) -> None:
        vars_in_func = self.local_vars[self.current_function]
        vars_in_func.append(LocalVar(name, ty))

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

    def stmt(self) -> GenNode:
        if self.consume_kind(TokenKind.RETURN):
            node = self.expr()
            self.expect(";")
            return ReturnNode(node)
        elif self.consume("int"):
            ty = Type(TypeKind.INT)

            while self.consume("*"):
                ty = Type(TypeKind.PTR, ty)

            tok = self.expect_ident()

            # array check
            if self.consume("["):
                array_size = self.expect_number()
                self.expect("]")
                ty = Type(TypeKind.ARRAY, ty, array_size=array_size)

            self.expect(";")

            self.register_local_var(tok.string, ty)
            return EmptyNode()
        elif self.consume_kind(TokenKind.IF):
            self.expect('(')
            n1 = self.expr()
            self.expect(')')
            n2 = self.stmt()

            # else clause
            n3 = None
            if self.consume_kind(TokenKind.ELSE):
                n3 = self.stmt()

            n = IfNode(n1, n2, n3)
            return n
        elif self.consume_kind(TokenKind.WHILE):
            self.expect('(')
            n1 = self.expr()
            self.expect(')')
            n2 = self.stmt()

            nw = WhileNode(n1, n2)
            return nw
        elif self.consume_kind(TokenKind.FOR):
            self.expect('(')
            n1 = None
            n2 = None
            n3 = None
            if not self.consume(';'):
                n1 = self.expr()
                self.expect(';')
            if not self.consume(';'):
                n2 = self.expr()
                self.expect(';')
            if not self.consume(')'):
                n3 = self.expr()
                self.expect(')')
            n4 = self.stmt()

            nf = ForNode(n1, n2, n3, n4)
            return nf
        elif self.consume("{"):
            block = BlockNode()
            while True:
                if self.consume("}"):
                    return block
                block.append(self.stmt())
        else:
            node = self.expr()
            self.expect(";")
            return node

    def expr(self) -> TypedNode:
        return self.assign()

    def assign(self) -> TypedNode:
        node = self.equality()
        if self.consume("="):
            node = BinaryNode(NodeKind.ASSIGN, node, self.assign())
        return node

    def equality(self) -> TypedNode:
        node = self.relational()
        while True:
            if self.consume("=="):
                node = BinaryNode(NodeKind.EQ, node, self.relational())
            elif self.consume("!="):
                node = BinaryNode(NodeKind.NEQ, node, self.relational())
            else:
                break
        return node

    def relational(self) -> TypedNode:
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

    def add(self) -> TypedNode:
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

    def mul(self) -> TypedNode:
        node = self.unary()
        while True:
            if self.consume("*"):
                node = BinaryNode(NodeKind.MUL, node, self.unary())
            elif self.consume("/"):
                node = BinaryNode(NodeKind.DIV, node, self.unary())
            else:
                break
        return node

    def unary(self) -> TypedNode:
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

    def subscript(self) -> TypedNode:
        p = self.primary()
        if self.consume("["):
            index = self.expr()
            self.expect("]")
            add = BinaryNode(NodeKind.ADD, p, index)
            deref = UnaryNode(NodeKind.DEREF, add)
            return deref
        return p

    def primary(self) -> TypedNode:
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
            if lvar is None:
                raise ParserError(
                    f"local variable {ident.string} is not defined.")
            return LVarNode(lvar)
