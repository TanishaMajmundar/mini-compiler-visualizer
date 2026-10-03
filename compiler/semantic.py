"""Phase 3: Semantic analysis.

Input : Node (tree from the parser)
Output: (list of Symbol, list of CompileError)   # the list holds errors AND warnings

The parser only checks the SHAPE of the program. This phase checks MEANING:
  * a variable must be declared before it is used        (error)
  * a variable cannot be declared twice in the same scope (error)
  * assigning a float value to an int variable            (warning)

Scopes: the top level is "global". Every { } block opens a new scope, so a
variable declared inside a block is not visible after the block ends.
We keep a stack of scopes (a list of dictionaries). Lookup searches from the
innermost scope outwards.

Unlike the parser, this phase does NOT stop at the first problem: it reports
all of them, because the tree is still perfectly walkable.
"""

from dataclasses import dataclass

from compiler.errors import CompileError
from compiler.parser import Node


@dataclass
class Symbol:
    """One row of the symbol table."""

    name: str
    type: str    # "int" or "float"
    scope: str   # "global", "block 1", "block 2", ...
    line: int    # line of the declaration


class Analyzer:
    """Walks the tree once, keeping the scope stack and collecting issues."""

    def __init__(self) -> None:
        self.scopes: list[dict[str, Symbol]] = [{}]   # scopes[0] is global
        self.scope_names: list[str] = ["global"]
        self.block_count = 0
        self.symbols: list[Symbol] = []               # every symbol ever declared
        self.issues: list[CompileError] = []

    # ---------- reporting ----------------------------------------------

    def error(self, message: str, line: int) -> None:
        self.issues.append(CompileError("Semantic", message, line, "error"))

    def warning(self, message: str, line: int) -> None:
        self.issues.append(CompileError("Semantic", message, line, "warning"))

    # ---------- symbol table operations --------------------------------

    def lookup(self, name: str) -> Symbol | None:
        """Search the innermost scope first, then outwards."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def declare(self, name: str, type_name: str, line: int) -> None:
        """Add a variable to the current scope (error if already there)."""
        current = self.scopes[-1]
        if name in current:
            first = current[name]
            self.error(
                f"'{name}' is already declared in this scope "
                f"(first declared on line {first.line})",
                line,
            )
            return
        symbol = Symbol(name, type_name, self.scope_names[-1], line)
        current[name] = symbol
        self.symbols.append(symbol)

    # ---------- statements ---------------------------------------------

    def visit_stmt(self, node: Node) -> None:
        if node.kind == "Decl":
            self.visit_decl(node)
        elif node.kind == "Assign":
            self.visit_assign(node)
        elif node.kind == "If":
            self.type_of(node.children[0])          # check the condition
            for block in node.children[1:]:          # then-block, else-block
                self.visit_block(block)
        elif node.kind == "While":
            self.type_of(node.children[0])
            self.visit_block(node.children[1])
        elif node.kind == "Block":
            self.visit_block(node)

    def visit_block(self, node: Node) -> None:
        """Enter a new scope, check the statements, leave the scope."""
        self.block_count += 1
        self.scopes.append({})
        self.scope_names.append(f"block {self.block_count}")
        for statement in node.children:
            self.visit_stmt(statement)
        self.scopes.pop()
        self.scope_names.pop()

    def visit_decl(self, node: Node) -> None:
        name_node = node.children[0]
        declared_type = node.label
        value_type = None
        if len(node.children) > 1:
            # Check the initializer BEFORE declaring, so "int x = x;" is an error.
            value_type = self.type_of(node.children[1])
        self.declare(name_node.label, declared_type, name_node.line)
        self.check_mismatch(name_node.label, declared_type, value_type, name_node.line)

    def visit_assign(self, node: Node) -> None:
        target = node.children[0]
        value_type = self.type_of(node.children[1])
        symbol = self.lookup(target.label)
        if symbol is None:
            self.error(f"'{target.label}' used before declaration", target.line)
            return
        self.check_mismatch(target.label, symbol.type, value_type, target.line)

    def check_mismatch(self, name: str, var_type: str, value_type: str | None, line: int) -> None:
        """Warn when a float value goes into an int variable."""
        if var_type == "int" and value_type == "float":
            self.warning(
                f"float value assigned to int variable '{name}' (decimal part will be lost)",
                line,
            )

    # ---------- expressions --------------------------------------------

    def type_of(self, node: Node) -> str | None:
        """Check an expression and return its type ("int" / "float").

        Returns None when the type is unknown (an undeclared variable was
        involved). That stops one mistake from causing a chain of errors.
        """
        if node.kind == "Num":
            return "float" if "." in node.label else "int"
        if node.kind == "Id":
            symbol = self.lookup(node.label)
            if symbol is None:
                self.error(f"'{node.label}' used before declaration", node.line)
                return None
            return symbol.type
        # BinOp or Cond: check BOTH sides so every error inside is reported.
        left = self.type_of(node.children[0])
        right = self.type_of(node.children[1])
        if left is None or right is None:
            return None
        return "float" if "float" in (left, right) else "int"


def analyze(tree: Node) -> tuple[list[Symbol], list[CompileError]]:
    """Run semantic analysis. Returns (symbol table, errors + warnings)."""
    analyzer = Analyzer()
    for statement in tree.children:
        analyzer.visit_stmt(statement)
    return analyzer.symbols, analyzer.issues