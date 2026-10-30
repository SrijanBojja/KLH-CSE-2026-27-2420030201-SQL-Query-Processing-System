"""
parser.py - Recursive Descent Parser for QueryForge SQL System
Parses tokens produced by SQLLexer into a strongly-typed Abstract Syntax Tree (AST).
Validates grammar, reports syntax errors with exact token coordinates,
and pretty-prints the parsed structure.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from lexer import Token, SQLLexer, LexerError


class ParserError(Exception):
    """Raised when syntax analysis fails."""
    def __init__(self, message: str, token: Optional[Token] = None):
        if token and token.token_type != "EOF":
            super().__init__(f"Syntax Error at Token #{token.position} ('{token.lexeme}' at Line {token.line}, Col {token.column}): {message}")
        elif token:
            super().__init__(f"Syntax Error at End of Query (Line {token.line}, Col {token.column}): {message}")
        else:
            super().__init__(f"Syntax Error: {message}")
        self.message = message
        self.token = token


# =====================================================================
# AST Node Classes
# =====================================================================

@dataclass
class ColumnRef:
    """Represents a column, optionally prefixed with a table name or alias (e.g., s.marks)."""
    column: str
    table_prefix: Optional[str] = None

    def __str__(self) -> str:
        if self.table_prefix:
            return f"{self.table_prefix}.{self.column}"
        return self.column


@dataclass
class Literal:
    """Represents literal values: numbers, quoted strings, NULL, booleans."""
    value: Any
    raw_type: str  # 'NUMBER', 'STRING', 'NULL', 'BOOLEAN'

    def __str__(self) -> str:
        if self.raw_type == 'STRING':
            return f"'{self.value}'"
        return str(self.value)


@dataclass
class BinaryOp:
    """Represents a binary operator expression (e.g., marks > 80, a AND b)."""
    left: Any
    op: str
    right: Any

    def __str__(self) -> str:
        return f"({self.left} {self.op} {self.right})"


@dataclass
class UnaryOp:
    """Represents a unary operator expression (e.g., NOT condition)."""
    op: str
    operand: Any

    def __str__(self) -> str:
        return f"({self.op} {self.operand})"


@dataclass
class AggregateCall:
    """Represents aggregate function calls like COUNT(*), AVG(marks)."""
    func_name: str
    argument: Union[ColumnRef, str]  # ColumnRef or '*'

    def __str__(self) -> str:
        return f"{self.func_name}({self.argument})"


@dataclass
class SelectItem:
    """A projected item in the SELECT list, with optional alias."""
    expression: Any  # ColumnRef, AggregateCall, '*', or Literal
    alias: Optional[str] = None

    def __str__(self) -> str:
        s = str(self.expression)
        if self.alias:
            s += f" AS {self.alias}"
        return s


@dataclass
class TableRef:
    """A table name with an optional alias."""
    name: str
    alias: Optional[str] = None

    def __str__(self) -> str:
        if self.alias:
            return f"{self.name} AS {self.alias}"
        return self.name


@dataclass
class JoinClause:
    """Represents an INNER JOIN or JOIN clause."""
    join_type: str  # 'INNER JOIN' or 'JOIN'
    table: TableRef
    on_condition: BinaryOp

    def __str__(self) -> str:
        return f"{self.join_type} {self.table} ON {self.on_condition}"


@dataclass
class OrderItem:
    """Represents an ORDER BY item with direction."""
    expression: ColumnRef
    direction: str = "ASC"  # 'ASC' or 'DESC'

    def __str__(self) -> str:
        return f"{self.expression} {self.direction}"


@dataclass
class ParsedQuery:
    """Top-level AST Node representing a parsed SQL SELECT query."""
    distinct: bool = False
    select_items: List[SelectItem] = field(default_factory=list)
    from_table: Optional[TableRef] = None
    joins: List[JoinClause] = field(default_factory=list)
    where_clause: Optional[Any] = None
    group_by: List[ColumnRef] = field(default_factory=list)
    order_by: List[OrderItem] = field(default_factory=list)
    limit: Optional[int] = None
    raw_query: str = ""

    def pretty_tree(self) -> str:
        """Produces a formatted, hierarchical representation of the AST."""
        lines = ["Parsed Query Structure:"]

        # SELECT
        sel_desc = "SELECT" + (" DISTINCT" if self.distinct else "")
        lines.append(f"  |-- {sel_desc}:")
        for i, item in enumerate(self.select_items):
            prefix = "  |   \\-- " if i == len(self.select_items) - 1 else "  |   |-- "
            lines.append(f"{prefix}{item}")

        # FROM
        lines.append(f"  |-- FROM: {self.from_table}")

        # JOINS
        if self.joins:
            lines.append("  |-- JOINS:")
            for j, join in enumerate(self.joins):
                j_prefix = "  |   \\-- " if j == len(self.joins) - 1 else "  |   |-- "
                lines.append(f"{j_prefix}{join}")

        # WHERE
        if self.where_clause:
            lines.append(f"  |-- WHERE: {self.where_clause}")

        # GROUP BY
        if self.group_by:
            lines.append(f"  |-- GROUP BY: {', '.join(str(c) for c in self.group_by)}")

        # ORDER BY
        if self.order_by:
            lines.append(f"  |-- ORDER BY: {', '.join(str(o) for o in self.order_by)}")

        # LIMIT
        if self.limit is not None:
            lines.append(f"  \\-- LIMIT: {self.limit}")
        else:
            lines.append("  \\-- LIMIT: None")

        return "\n".join(lines)


# =====================================================================
# Recursive Descent Parser Implementation
# =====================================================================

class SQLParser:
    """
    Parses a token stream using recursive descent.
    Supports a clear, rigorous subset of SQL SELECT queries.
    """

    def __init__(self, tokens: List[Token], raw_query: str = ""):
        self.tokens = tokens
        self.raw_query = raw_query
        self.pos = 0

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def _peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def _check(self, token_type: str, lexeme: Optional[str] = None) -> bool:
        t = self._current()
        if t.token_type != token_type:
            return False
        if lexeme is not None and t.lexeme.upper() != lexeme.upper():
            return False
        return True

    def _match(self, token_type: str, lexeme: Optional[str] = None) -> bool:
        if self._check(token_type, lexeme):
            self.pos += 1
            return True
        return False

    def _consume(self, token_type: str, lexeme: Optional[str] = None, error_msg: str = "") -> Token:
        t = self._current()
        if self._check(token_type, lexeme):
            self.pos += 1
            return t
        expected = f"{token_type} ('{lexeme}')" if lexeme else token_type
        msg = error_msg or f"Expected {expected}, but found '{t.lexeme}'"
        raise ParserError(msg, t)

    def parse(self) -> ParsedQuery:
        """Top-level entry point for parsing an SQL query."""
        if not self.tokens or (len(self.tokens) == 1 and self.tokens[0].token_type == "EOF"):
            raise ParserError("Empty query: Please enter an SQL query to process.")

        # Guard against non-SELECT queries
        curr = self._current()
        if curr.token_type == "KEYWORD" and curr.lexeme.upper() in {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"}:
            raise ParserError(
                f"Unsupported statement '{curr.lexeme.upper()}'. QueryForge is an educational SELECT query processing compiler pipeline.",
                curr
            )

        if not self._check("KEYWORD", "SELECT"):
            raise ParserError(f"Query must begin with 'SELECT', found '{curr.lexeme}'", curr)

        parsed = self._parse_select_statement()

        # Optional semicolon
        if self._check("SEMICOLON"):
            self._advance()

        # Must be at EOF
        if not self._check("EOF"):
            extra = self._current()
            raise ParserError(f"Unexpected token '{extra.lexeme}' after valid query end", extra)

        parsed.raw_query = self.raw_query
        return parsed

    def _advance(self) -> Token:
        t = self._current()
        if self.pos < len(self.tokens):
            self.pos += 1
        return t

    def _parse_select_statement(self) -> ParsedQuery:
        query = ParsedQuery()
        self._consume("KEYWORD", "SELECT")

        # Optional DISTINCT
        if self._match("KEYWORD", "DISTINCT"):
            query.distinct = True

        # Parse select list
        query.select_items = self._parse_select_list()

        # Must have FROM clause
        if not self._match("KEYWORD", "FROM"):
            curr = self._current()
            raise ParserError("Expected 'FROM' clause following column list", curr)

        query.from_table = self._parse_table_reference()

        # Parse zero or more JOIN clauses
        while self._check("KEYWORD", "JOIN") or (self._check("KEYWORD", "INNER") and self._peek(1).lexeme.upper() == "JOIN"):
            query.joins.append(self._parse_join_clause())

        # Optional WHERE clause
        if self._match("KEYWORD", "WHERE"):
            query.where_clause = self._parse_where_condition()

        # Optional GROUP BY clause
        if self._match("KEYWORD", "GROUP"):
            self._consume("KEYWORD", "BY", error_msg="Expected 'BY' after 'GROUP'")
            query.group_by = self._parse_group_by_list()

        # Optional ORDER BY clause
        if self._match("KEYWORD", "ORDER"):
            self._consume("KEYWORD", "BY", error_msg="Expected 'BY' after 'ORDER'")
            query.order_by = self._parse_order_by_list()

        # Optional LIMIT clause
        if self._match("KEYWORD", "LIMIT"):
            lim_tok = self._consume("NUMBER", error_msg="Expected an integer constant following 'LIMIT'")
            try:
                query.limit = int(lim_tok.lexeme)
            except ValueError:
                raise ParserError(f"Invalid integer for LIMIT: '{lim_tok.lexeme}'", lim_tok)

        return query

    def _parse_select_list(self) -> List[SelectItem]:
        items = []

        # Check for SELECT *
        if self._match("ASTERISK"):
            items.append(SelectItem(expression="*"))
            return items

        while True:
            items.append(self._parse_select_item())
            if self._match("COMMA"):
                continue
            break

        return items

    def _parse_select_item(self) -> SelectItem:
        curr = self._current()

        # Check for aggregate function: COUNT, SUM, AVG, MIN, MAX
        if curr.token_type == "KEYWORD" and curr.lexeme.upper() in {"COUNT", "SUM", "AVG", "MIN", "MAX"}:
            func_tok = self._advance()
            func_name = func_tok.lexeme.upper()
            self._consume("LPAREN", error_msg=f"Expected '(' after aggregate function {func_name}")

            if self._match("ASTERISK"):
                arg = "*"
            else:
                arg = self._parse_column_ref()

            self._consume("RPAREN", error_msg=f"Expected ')' closing aggregate function {func_name}")
            expr = AggregateCall(func_name, arg)
        else:
            expr = self._parse_column_ref()

        # Check for optional alias: [AS] alias_name
        alias = None
        if self._match("KEYWORD", "AS"):
            alias_tok = self._consume("IDENTIFIER", error_msg="Expected alias identifier after 'AS'")
            alias = alias_tok.lexeme
        elif self._check("IDENTIFIER") and self._current().lexeme.upper() not in {"FROM", "WHERE", "JOIN", "ORDER", "GROUP", "LIMIT"}:
            # Implicit alias without 'AS'
            alias = self._advance().lexeme

        return SelectItem(expression=expr, alias=alias)

    def _parse_column_ref(self) -> ColumnRef:
        curr = self._consume("IDENTIFIER", error_msg="Expected column identifier")
        # Check for table qualification: tbl.col
        if self._match("PERIOD"):
            col_tok = self._consume("IDENTIFIER", error_msg="Expected column name after '.'")
            return ColumnRef(column=col_tok.lexeme, table_prefix=curr.lexeme)
        return ColumnRef(column=curr.lexeme)

    def _parse_table_reference(self) -> TableRef:
        tbl_tok = self._consume("IDENTIFIER", error_msg="Expected table name in FROM clause")
        alias = None
        if self._match("KEYWORD", "AS"):
            alias_tok = self._consume("IDENTIFIER", error_msg="Expected alias name after 'AS'")
            alias = alias_tok.lexeme
        elif self._check("IDENTIFIER") and self._current().lexeme.upper() not in {"WHERE", "JOIN", "INNER", "ORDER", "GROUP", "LIMIT", "ON"}:
            alias = self._advance().lexeme

        return TableRef(name=tbl_tok.lexeme, alias=alias)

    def _parse_join_clause(self) -> JoinClause:
        join_type = "INNER JOIN"
        if self._match("KEYWORD", "INNER"):
            self._consume("KEYWORD", "JOIN")
        else:
            self._consume("KEYWORD", "JOIN")

        table_ref = self._parse_table_reference()
        self._consume("KEYWORD", "ON", error_msg=f"Expected 'ON' condition for JOIN on table '{table_ref.name}'")
        on_cond = self._parse_where_condition()

        return JoinClause(join_type=join_type, table=table_ref, on_condition=on_cond)

    def _parse_group_by_list(self) -> List[ColumnRef]:
        items = []
        while True:
            items.append(self._parse_column_ref())
            if self._match("COMMA"):
                continue
            break
        return items

    def _parse_order_by_list(self) -> List[OrderItem]:
        items = []
        while True:
            col = self._parse_column_ref()
            direction = "ASC"
            if self._match("KEYWORD", "ASC"):
                direction = "ASC"
            elif self._match("KEYWORD", "DESC"):
                direction = "DESC"
            items.append(OrderItem(expression=col, direction=direction))
            if self._match("COMMA"):
                continue
            break
        return items

    # -------------------------------------------------------------
    # Expression Parsing (Precedence: OR -> AND -> Comparisons)
    # -------------------------------------------------------------

    def _parse_where_condition(self) -> Any:
        return self._parse_or_expr()

    def _parse_or_expr(self) -> Any:
        left = self._parse_and_expr()
        while self._match("KEYWORD", "OR"):
            right = self._parse_and_expr()
            left = BinaryOp(left=left, op="OR", right=right)
        return left

    def _parse_and_expr(self) -> Any:
        left = self._parse_comparison_expr()
        while self._match("KEYWORD", "AND"):
            right = self._parse_comparison_expr()
            left = BinaryOp(left=left, op="AND", right=right)
        return left

    def _parse_comparison_expr(self) -> Any:
        # Check for parenthesized expression: (expr)
        if self._match("LPAREN"):
            inner = self._parse_where_condition()
            self._consume("RPAREN", error_msg="Expected ')' closing parenthesized condition")
            return inner

        # Check for NOT
        if self._match("KEYWORD", "NOT"):
            operand = self._parse_comparison_expr()
            return UnaryOp(op="NOT", operand=operand)

        left = self._parse_primary_term()

        # Check for IS NULL / IS NOT NULL
        if self._match("KEYWORD", "IS"):
            if self._match("KEYWORD", "NOT"):
                self._consume("KEYWORD", "NULL", error_msg="Expected 'NULL' after 'IS NOT'")
                return BinaryOp(left=left, op="IS NOT", right=Literal(value=None, raw_type="NULL"))
            else:
                self._consume("KEYWORD", "NULL", error_msg="Expected 'NULL' after 'IS'")
                return BinaryOp(left=left, op="IS", right=Literal(value=None, raw_type="NULL"))

        # Comparison operators: =, !=, <>, <, >, <=, >=
        if self._check("OPERATOR"):
            op_tok = self._advance()
            right = self._parse_primary_term()
            return BinaryOp(left=left, op=op_tok.lexeme, right=right)

        return left

    def _parse_primary_term(self) -> Any:
        curr = self._current()

        if curr.token_type == "NUMBER":
            self._advance()
            val = float(curr.lexeme) if '.' in curr.lexeme else int(curr.lexeme)
            return Literal(value=val, raw_type="NUMBER")

        if curr.token_type == "STRING":
            self._advance()
            # Strip quotes
            clean_str = curr.lexeme[1:-1]
            return Literal(value=clean_str, raw_type="STRING")

        if curr.token_type == "KEYWORD" and curr.lexeme.upper() == "NULL":
            self._advance()
            return Literal(value=None, raw_type="NULL")

        if curr.token_type == "IDENTIFIER":
            return self._parse_column_ref()

        raise ParserError(f"Unexpected token '{curr.lexeme}' in expression", curr)


def parse_sql(sql_text: str) -> ParsedQuery:
    """Convenience helper to tokenize and parse an SQL query."""
    lexer = SQLLexer(sql_text)
    tokens = lexer.tokenize()
    parser = SQLParser(tokens, raw_query=sql_text)
    return parser.parse()


if __name__ == "__main__":
    queries = [
        "SELECT * FROM students;",
        "SELECT name, marks FROM students WHERE marks > 80;",
        "SELECT name, marks FROM students ORDER BY marks DESC LIMIT 5;",
        "SELECT department, AVG(marks) AS average_marks FROM students GROUP BY department;",
        "SELECT s.name, c.course_name, e.grade FROM students s INNER JOIN enrollments e ON s.student_id = e.student_id INNER JOIN courses c ON e.course_id = c.course_id;"
    ]

    for q in queries:
        print("=" * 60)
        print("QUERY:", q)
        ast = parse_sql(q)
        print(ast.pretty_tree())
