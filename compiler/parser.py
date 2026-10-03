"""Phase 2: Syntax analysis (recursive descent parser).

Input : list of Token (from the lexer)
Output: Node (root of the tree). Raises CompileError on the first syntax error.

Grammar (left recursion replaced by loops):

    Program -> Stmt*
    Stmt    -> Decl | Assign | If | While | Block
    Decl    -> (int | float) id [ = Expr ] ;
    Assign  -> id = Expr ;
    If      -> if ( Cond ) Block [ else Block ]
    While   -> while ( Cond ) Block
    Block   -> { Stmt* }
    Cond    -> Expr relop Expr
    Expr    -> Term { (+ | -) Term }
    Term    -> Factor { (* | /) Factor }
    Factor  -> ( Expr ) | id | num

Precedence comes from the grammar levels: Term (* /) sits below Expr (+ -),
so * and / bind tighter. Using a loop on the left makes the operators
left-associative:  8 - 3 - 2  is  (8 - 3) - 2.

The tree is an AST (abstract syntax tree): no nodes for ';', '(' or '{'.
"""

from dataclasses import dataclass, field

from compiler.errors import CompileError
from compiler.lexer import Token


@dataclass
class Node:
    """One node of the tree.

    kind     -> Program, Decl, Assign, If, While, Block, Cond, BinOp, Id, Num
    label    -> text shown in the drawing: "=", "+", "x", "5", "int"
    children -> sub-nodes (empty for leaves like Id and Num)
    line     -> source line where it starts

    Children layout for the statement nodes:
        Decl  : [Id, init_expr?]        label = the type ("int" / "float")
        Assign: [Id, expr]
        If    : [Cond, then_Block, else_Block?]
        While : [Cond, Block]
        Block : [statements...]
        Cond  : [left_expr, right_expr] label = the relational operator
    """

    kind: str
    label: str
    children: list["Node"] = field(default_factory=list)
    line: int = 0


def _describe(token: Token) -> str:
    """How a token is written inside an error message."""
    if token.type == "EOF":
        return "end of file"
    return f"'{token.lexeme}'"


class Parser:
    """Holds the token list and our current position in it."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    # ---------- small helpers ------------------------------------------

    def peek(self) -> Token:
        """Look at the current token without consuming it."""
        return self.tokens[self.pos]

    def advance(self) -> Token:
        """Consume and return the current token (never moves past EOF)."""
        token = self.tokens[self.pos]
        if token.type != "EOF":
            self.pos += 1
        return token

    def fail(self, expected: str, line: int | None = None) -> CompileError:
        """Build the 'expected X but found Y' error for the current token."""
        found = self.peek()
        return CompileError(
            "Syntax",
            f"expected {expected} but found {_describe(found)}",
            found.line if line is None else line,
        )

    def expect(self, token_type: str, shown: str, report_previous_line: bool = False) -> Token:
        """Consume a token of the given type, or raise a syntax error.

        report_previous_line is used for ';': if it is missing, the mistake is
        at the END of the previous line, not on the next statement's line.
        """
        if self.peek().type == token_type:
            return self.advance()
        line = None
        if report_previous_line and self.pos > 0:
            line = self.tokens[self.pos - 1].line
        raise self.fail(shown, line)

    def at_keyword(self, word: str) -> bool:
        """True if the current token is the given keyword."""
        token = self.peek()
        return token.type == "KEYWORD" and token.lexeme == word

    # ---------- statements ---------------------------------------------

    def parse_program(self) -> Node:
        """Program -> Stmt*"""
        statements = []
        while self.peek().type != "EOF":
            statements.append(self.parse_stmt())
        return Node("Program", "Program", statements, line=1)

    def parse_stmt(self) -> Node:
        """Stmt -> Decl | Assign | If | While | Block

        The first token tells us which rule to use (no backtracking needed).
        """
        token = self.peek()
        if token.type == "KEYWORD":
            if token.lexeme in ("int", "float"):
                return self.parse_decl()
            if token.lexeme == "if":
                return self.parse_if()
            if token.lexeme == "while":
                return self.parse_while()
        elif token.type == "ID":
            return self.parse_assign()
        elif token.type == "LBRACE":
            return self.parse_block()
        raise self.fail("a statement")

    def parse_decl(self) -> Node:
        """Decl -> (int | float) id [ = Expr ] ;"""
        type_token = self.advance()
        name = self.expect("ID", "identifier")
        children = [Node("Id", name.lexeme, [], name.line)]
        if self.peek().type == "ASSIGN":
            self.advance()
            children.append(self.parse_expr())
        self.expect("SEMI", "';'", report_previous_line=True)
        return Node("Decl", type_token.lexeme, children, type_token.line)

    def parse_assign(self) -> Node:
        """Assign -> id = Expr ;"""
        name = self.advance()
        self.expect("ASSIGN", "'='")
        value = self.parse_expr()
        self.expect("SEMI", "';'", report_previous_line=True)
        target = Node("Id", name.lexeme, [], name.line)
        return Node("Assign", "=", [target, value], name.line)

    def parse_if(self) -> Node:
        """If -> if ( Cond ) Block [ else Block ]"""
        keyword = self.advance()
        condition = self.parse_condition()
        then_block = self.parse_block()
        children = [condition, then_block]
        if self.at_keyword("else"):
            self.advance()
            children.append(self.parse_block())
        return Node("If", "if", children, keyword.line)

    def parse_while(self) -> Node:
        """While -> while ( Cond ) Block"""
        keyword = self.advance()
        condition = self.parse_condition()
        body = self.parse_block()
        return Node("While", "while", [condition, body], keyword.line)

    def parse_block(self) -> Node:
        """Block -> { Stmt* }"""
        open_brace = self.expect("LBRACE", "'{'")
        statements = []
        while self.peek().type not in ("RBRACE", "EOF"):
            statements.append(self.parse_stmt())
        self.expect("RBRACE", "'}'")
        return Node("Block", "{ }", statements, open_brace.line)

    def parse_condition(self) -> Node:
        """( Cond )  where  Cond -> Expr relop Expr

        The parentheses belong to the if/while statement, so they are
        consumed here and do not appear in the tree.
        """
        self.expect("LPAREN", "'('")
        left = self.parse_expr()
        if self.peek().type != "RELOP":
            raise self.fail("relational operator (<, >, <=, >=, ==, !=)")
        op = self.advance()
        right = self.parse_expr()
        self.expect("RPAREN", "')'")
        return Node("Cond", op.lexeme, [left, right], op.line)

    # ---------- expressions --------------------------------------------

    def parse_expr(self) -> Node:
        """Expr -> Term { (+ | -) Term }"""
        left = self.parse_term()
        while self.peek().type == "OP" and self.peek().lexeme in ("+", "-"):
            op = self.advance()
            right = self.parse_term()
            left = Node("BinOp", op.lexeme, [left, right], op.line)
        return left

    def parse_term(self) -> Node:
        """Term -> Factor { (* | /) Factor }"""
        left = self.parse_factor()
        while self.peek().type == "OP" and self.peek().lexeme in ("*", "/"):
            op = self.advance()
            right = self.parse_factor()
            left = Node("BinOp", op.lexeme, [left, right], op.line)
        return left

    def parse_factor(self) -> Node:
        """Factor -> ( Expr ) | id | num"""
        token = self.peek()
        if token.type == "LPAREN":
            self.advance()
            inner = self.parse_expr()
            self.expect("RPAREN", "')'")
            return inner
        if token.type == "ID":
            self.advance()
            return Node("Id", token.lexeme, [], token.line)
        if token.type == "NUM":
            self.advance()
            return Node("Num", token.lexeme, [], token.line)
        raise self.fail("identifier, number or '('")


def parse(tokens: list[Token]) -> Node:
    """Parse a token list into a tree. Raises CompileError on a syntax error."""
    return Parser(tokens).parse_program()