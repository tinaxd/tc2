from enum import Enum


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
    def __init__(self, kind, string, val=None):
        self.kind = kind
        self.string = string
        self.val = val


class NodeKind(Enum):
    ND_ADD = 1
    ND_SUB = 2
    ND_MUL = 3
    ND_DIV = 4
    ND_LT = 5
    ND_LE = 6
    ND_EQ = 7
    ND_NEQ = 8
    ND_ASSIGN = 9
    ND_NUM = 10
    ND_RETURN = 11
    ND_IF = 12
    ND_WHILE = 13
    ND_FOR = 14
    ND_BLOCK = 15
    ND_CALL = 16
    ND_DEF = 17
    ND_DEREF = 18
    ND_ADDR = 19
    ND_EMPTY = 20
    ND_LVAR = 21
