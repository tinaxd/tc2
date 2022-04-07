import unittest
from tc2.parser import BinaryNode, NodeKind, NumNode, Parser, tokenize, TokenKind, Token
TK = TokenKind


class TokenizerTest(unittest.TestCase):
    def test_tokenizer_add(self):
        s = "1 + 3"
        tokens = tokenize(s)
        self.assertListEqual(
            tokens,
            [
                Token(TokenKind.NUM, "1", 1),
                Token(TokenKind.RESERVED, "+"),
                Token(TokenKind.NUM, "3", 3),
                Token(TokenKind.EOF, "")
            ]
        )

    def test_tokenizer_mul(self):
        s = "10 * 3"
        tokens = tokenize(s)
        self.assertListEqual(
            tokens,
            [
                Token(TokenKind.NUM, "10", 10),
                Token(TokenKind.RESERVED, "*"),
                Token(TokenKind.NUM, "3", 3),
                Token(TokenKind.EOF, "")
            ]
        )

    def test_tokenizer_main(self):
        s = "int main() { return 0; }"
        tokens = tokenize(s)
        self.assertListEqual(
            tokens,
            [
                Token(TK.RESERVED, "int"),
                Token(TK.IDENT, "main"),
                Token(TK.RESERVED, "("),
                Token(TK.RESERVED, ")"),
                Token(TK.RESERVED, "{"),
                Token(TK.RETURN, "return"),
                Token(TK.NUM, "0", 0),
                Token(TK.RESERVED, ";"),
                Token(TK.RESERVED, "}"),
                Token(TK.EOF, "")
            ]
        )


class ParserTest(unittest.TestCase):
    def test_expr_add(self):
        tokens = tokenize("13+3")
        parser = Parser(tokens)
        node = parser.expr()
        self.assertEqual(node.kind, NodeKind.ADD)
        self.assertIsInstance(node, BinaryNode)
        self.assertIsInstance(node.lhs, NumNode)
        self.assertIsInstance(node.rhs, NumNode)
        self.assertEqual(node.lhs.val, 13)
        self.assertEqual(node.rhs.val, 3)

    def test_expr_mul_order(self):
        tokens = tokenize("13+3*4")
        parser = Parser(tokens)
        node = parser.expr()
        self.assertEqual(node.kind, NodeKind.ADD)
        self.assertIsInstance(node, BinaryNode)
        self.assertIsInstance(node.lhs, NumNode)
        self.assertIsInstance(node.rhs, BinaryNode)
        self.assertEqual(node.rhs.kind, NodeKind.MUL)
        self.assertIsInstance(node.rhs.lhs, NumNode)
        self.assertIsInstance(node.rhs.rhs, NumNode)
        self.assertEqual(node.rhs.lhs.val, 3)
        self.assertEqual(node.rhs.rhs.val, 4)

    def test_expr_mul_order2(self):
        tokens = tokenize("3*4+13")
        parser = Parser(tokens)
        node = parser.expr()
        self.assertEqual(node.kind, NodeKind.ADD)
        self.assertIsInstance(node, BinaryNode)
        self.assertIsInstance(node.rhs, NumNode)
        self.assertIsInstance(node.lhs, BinaryNode)
        self.assertEqual(node.lhs.kind, NodeKind.MUL)
        self.assertIsInstance(node.lhs.lhs, NumNode)
        self.assertIsInstance(node.lhs.rhs, NumNode)
        self.assertEqual(node.lhs.lhs.val, 3)
        self.assertEqual(node.lhs.rhs.val, 4)

    def test_func_main(self):
        s = "int main() { return 0; }"
        tokens = tokenize(s)
        parser = Parser(tokens)
        node = parser.program()
        self.assertEqual(len(node), 1)
        node = node[0]
        self.assertEqual(node.kind, NodeKind.DEF)
        self.assertEqual(node.funcname, "main")
        self.assertEqual(node.body.kind, NodeKind.BLOCK)
        self.assertEqual(len(node.body.stmts), 1)
        stmt = node.body.stmts[0]
        self.assertEqual(stmt.kind, NodeKind.RETURN)
        self.assertEqual(stmt.val.kind, NodeKind.NUM)
        self.assertEqual(stmt.val.val, 0)


if __name__ == '__main__':
    unittest.main()
