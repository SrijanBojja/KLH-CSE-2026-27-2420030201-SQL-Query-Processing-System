"""
lexer.py - Lexical Analyzer / Tokenizer for QueryForge SQL System
Transforms a raw SQL query string into a stream of categorized tokens.
Tracks token positions, line, column, and provides educational descriptions.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class Token:
    """Represents a single lexical token in the SQL query."""
    position: int         # 1-based sequential position in the token stream
    token_type: str       # KEYWORD, IDENTIFIER, NUMBER, STRING, OPERATOR, etc.
    lexeme: str           # The textual slice from the source code
    line: int             # 1-based line number
    column: int           # 1-based column number

    def __repr__(self) -> str:
        return f"Token({self.position}, {self.token_type}, '{self.lexeme}', L{self.line}:C{self.column})"


TOKEN_TYPE_DESCRIPTIONS = {
    "KEYWORD": "Reserved SQL grammar term specifying query operations and structural clauses (e.g., SELECT, FROM, WHERE).",
    "IDENTIFIER": "Name referencing a database entity such as a table, column, or table alias.",
    "NUMBER": "Numeric literal constant (integer or decimal) used in filtering conditions, limits, or calculations.",
    "STRING": "Text literal constant enclosed in quotes representing literal character data.",
    "OPERATOR": "Relational or arithmetic symbol (=, !=, <, >, <=, >=) specifying an evaluation or comparison.",
    "COMMA": "Syntactic punctuation delimiter separating multiple expressions, columns, or items.",
    "PERIOD": "Member-access delimiter used to qualify a column with its source table or alias (e.g., s.name).",
    "SEMICOLON": "Statement termination delimiter signaling the end of the SQL query.",
    "LPAREN": "Opening parenthesis grouping an expression or enclosing function arguments.",
    "RPAREN": "Closing parenthesis concluding a grouped expression or argument list.",
    "ASTERISK": "Wildcard token indicating all columns in a table projection (*), or multiplication operator.",
    "EOF": "End of File/Input token indicating the parser has reached the end of the query string."
}

SQL_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "AND", "OR", "NOT",
    "ORDER", "BY", "ASC", "DESC", "LIMIT", "DISTINCT",
    "GROUP", "HAVING", "JOIN", "INNER", "LEFT", "RIGHT",
    "ON", "AS", "IS", "NULL", "COUNT", "SUM", "AVG", "MIN", "MAX"
}


class LexerError(Exception):
    """Custom exception raised for lexical analysis failures."""
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"Lexical Error at Line {line}, Column {column}: {message}")
        self.message = message
        self.line = line
        self.column = column


class SQLLexer:
    """
    Scans raw SQL query text and performs lexical analysis to generate tokens.
    """

    def __init__(self, source_sql: str):
        self.source = source_sql
        self.length = len(source_sql)
        self.cursor = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def _peek(self, offset: int = 0) -> Optional[str]:
        pos = self.cursor + offset
        if pos < self.length:
            return self.source[pos]
        return None

    def _advance(self) -> Optional[str]:
        if self.cursor < self.length:
            char = self.source[self.cursor]
            self.cursor += 1
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            return char
        return None

    def tokenize(self) -> List[Token]:
        """Tokenizes the complete SQL string into a list of Token objects."""
        self.tokens = []
        token_index = 1

        while self.cursor < self.length:
            char = self._peek()

            # Skip whitespace
            if char in (' ', '\t', '\r', '\n'):
                self._advance()
                continue

            # Skip single line comments (-- ...)
            if char == '-' and self._peek(1) == '-':
                while self._peek() is not None and self._peek() != '\n':
                    self._advance()
                continue

            token_line = self.line
            token_col = self.column

            # Delimiters and single-character symbols
            if char == ',':
                self._advance()
                self.tokens.append(Token(token_index, "COMMA", ",", token_line, token_col))
                token_index += 1
                continue

            if char == ';':
                self._advance()
                self.tokens.append(Token(token_index, "SEMICOLON", ";", token_line, token_col))
                token_index += 1
                continue

            if char == '(':
                self._advance()
                self.tokens.append(Token(token_index, "LPAREN", "(", token_line, token_col))
                token_index += 1
                continue

            if char == ')':
                self._advance()
                self.tokens.append(Token(token_index, "RPAREN", ")", token_line, token_col))
                token_index += 1
                continue

            if char == '.':
                self._advance()
                self.tokens.append(Token(token_index, "PERIOD", ".", token_line, token_col))
                token_index += 1
                continue

            if char == '*':
                self._advance()
                self.tokens.append(Token(token_index, "ASTERISK", "*", token_line, token_col))
                token_index += 1
                continue

            # Multi-character or single-character operators
            # !=, <>, <=, >=, =, <, >
            if char == '!' and self._peek(1) == '=':
                self._advance()
                self._advance()
                self.tokens.append(Token(token_index, "OPERATOR", "!=", token_line, token_col))
                token_index += 1
                continue

            if char == '<' and self._peek(1) == '>':
                self._advance()
                self._advance()
                self.tokens.append(Token(token_index, "OPERATOR", "<>", token_line, token_col))
                token_index += 1
                continue

            if char == '<' and self._peek(1) == '=':
                self._advance()
                self._advance()
                self.tokens.append(Token(token_index, "OPERATOR", "<=", token_line, token_col))
                token_index += 1
                continue

            if char == '>' and self._peek(1) == '=':
                self._advance()
                self._advance()
                self.tokens.append(Token(token_index, "OPERATOR", ">=", token_line, token_col))
                token_index += 1
                continue

            if char in ('=', '<', '>', '+', '-', '/'):
                self._advance()
                self.tokens.append(Token(token_index, "OPERATOR", char, token_line, token_col))
                token_index += 1
                continue

            # String Literals ('...' or "...")
            if char in ("'", '"'):
                quote_char = char
                self._advance()
                lexeme_chars = []
                closed = False

                while self._peek() is not None:
                    curr = self._advance()
                    if curr == quote_char:
                        # Handle escaped quote: '' or ""
                        if self._peek() == quote_char:
                            lexeme_chars.append(quote_char)
                            self._advance()
                        else:
                            closed = True
                            break
                    else:
                        lexeme_chars.append(curr)

                if not closed:
                    raise LexerError(f"Unterminated string literal starting with {quote_char}", token_line, token_col)

                string_val = "".join(lexeme_chars)
                self.tokens.append(Token(token_index, "STRING", f"'{string_val}'", token_line, token_col))
                token_index += 1
                continue

            # Numeric Literals (integer or floating point)
            if char.isdigit():
                num_chars = []
                has_dot = False
                while self._peek() is not None and (self._peek().isdigit() or (self._peek() == '.' and not has_dot)):
                    if self._peek() == '.':
                        # Lookahead: is the next character a digit? If not, could be member access
                        if self._peek(1) is not None and self._peek(1).isdigit():
                            has_dot = True
                            num_chars.append(self._advance())
                        else:
                            break
                    else:
                        num_chars.append(self._advance())

                num_str = "".join(num_chars)
                self.tokens.append(Token(token_index, "NUMBER", num_str, token_line, token_col))
                token_index += 1
                continue

            # Identifiers or Keywords (letters, underscores, or digits after start)
            if char.isalpha() or char == '_':
                ident_chars = []
                while self._peek() is not None and (self._peek().isalnum() or self._peek() == '_'):
                    ident_chars.append(self._advance())

                ident_str = "".join(ident_chars)
                upper_ident = ident_str.upper()

                if upper_ident in SQL_KEYWORDS:
                    self.tokens.append(Token(token_index, "KEYWORD", upper_ident, token_line, token_col))
                else:
                    self.tokens.append(Token(token_index, "IDENTIFIER", ident_str, token_line, token_col))

                token_index += 1
                continue

            # Unrecognized character
            bad_char = self._advance()
            raise LexerError(f"Unrecognized character '{bad_char}'", token_line, token_col)

        # Append EOF token
        self.tokens.append(Token(token_index, "EOF", "<EOF>", self.line, self.column))
        return self.tokens


if __name__ == "__main__":
    sample_sql = "SELECT name, marks FROM students WHERE marks > 80 ORDER BY marks DESC LIMIT 5;"
    lexer = SQLLexer(sample_sql)
    tokens = lexer.tokenize()
    print(f"Total Tokens: {len(tokens)}")
    for t in tokens:
        print(f"{t.position:>2} | {t.token_type:<10} | {t.lexeme}")

