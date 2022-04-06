import unittest
from .parser import tokenize, TokenKind, Token
TK = TokenKind


class ParserTest(unittest.TestCase):
    def test_tokenizer_add(self):
        s = "1 + 3"
        tokens = tokenize(s)
        self.assertListEqual(
            tokens,
            [
                Token(TokenKind.NUM, "1", 1),
                Token(TokenKind.RESERVED, "+"),
                Token(TokenKind.NUM, "3", 3)
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
                Token(TokenKind.NUM, "3", 3)
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
                Token(TK.RESERVED, "}")
            ]
        )


if __name__ == '__main__':
    unittest.main()
