from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import DefNode


class CFGNode:
    pass


class CFG:
    def __init__(self, func: 'DefNode') -> None:
        self.func = func
        self.nodes = []
        self.edges = []

    def analyze(self) -> None:
