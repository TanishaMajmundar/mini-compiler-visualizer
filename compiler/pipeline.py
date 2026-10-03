"""Runs every compiler phase in order and collects the results.

The UI only calls compile_source(); it never calls the phases directly.
The pipeline stops at the first phase that fails, but keeps the outputs of
all phases that finished (so the UI can still show them).
"""

from dataclasses import dataclass, field

from compiler.codegen import TACInstruction, Triple, generate, to_triples
from compiler.errors import CompileError
from compiler.lexer import Token, tokenize
from compiler.parser import Node, parse


@dataclass
class CompileResult:
    """Everything the UI needs. Fields stay empty/None if a phase did not run."""

    source: str
    tokens: list[Token] = field(default_factory=list)
    tree: Node | None = None
    tac: list[TACInstruction] = field(default_factory=list)
    triples: list[Triple] = field(default_factory=list)
    errors: list[CompileError] = field(default_factory=list)
    failed_phase: str | None = None   # "Lexical", "Syntax" or None if all OK

    @property
    def ok(self) -> bool:
        return not self.errors


def compile_source(source: str) -> CompileResult:
    """Compile source code through all implemented phases."""
    result = CompileResult(source=source)

    # Phase 1: lexer (may report several errors at once)
    tokens, lex_errors = tokenize(source)
    result.tokens = tokens
    if lex_errors:
        result.errors = lex_errors
        result.failed_phase = "Lexical"
        return result

    # Phase 2: parser (stops at the first syntax error)
    try:
        result.tree = parse(tokens)
    except CompileError as error:
        result.errors = [error]
        result.failed_phase = "Syntax"
        return result

    # Phase 4: code generation (TAC, then triples)
    result.tac = generate(result.tree)
    result.triples = to_triples(result.tac)
    return result
