"""Runs every compiler phase in order and collects the results.

The UI only calls compile_source(); it never calls the phases directly.
The pipeline stops at the first phase that fails, but keeps the outputs of
all phases that finished (so the UI can still show them).
Warnings never stop the pipeline.
"""

from dataclasses import dataclass, field

from compiler.codegen import TACInstruction, Triple, generate, to_triples
from compiler.errors import CompileError
from compiler.lexer import Token, tokenize
from compiler.optimizer import Change, optimize
from compiler.parser import Node, parse
from compiler.semantic import Symbol, analyze


@dataclass
class CompileResult:
    """Everything the UI needs. Fields stay empty/None if a phase did not run."""

    source: str
    tokens: list[Token] = field(default_factory=list)
    tree: Node | None = None
    symbols: list[Symbol] = field(default_factory=list)
    tac: list[TACInstruction] = field(default_factory=list)
    triples: list[Triple] = field(default_factory=list)
    optimized: list[TACInstruction] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    errors: list[CompileError] = field(default_factory=list)
    warnings: list[CompileError] = field(default_factory=list)
    failed_phase: str | None = None   # "Lexical", "Syntax", "Semantic" or None

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

    # Phase 3: semantic analysis (reports all errors and warnings)
    symbols, issues = analyze(result.tree)
    result.symbols = symbols
    result.warnings = [i for i in issues if i.severity == "warning"]
    semantic_errors = [i for i in issues if i.severity == "error"]
    if semantic_errors:
        result.errors = semantic_errors
        result.failed_phase = "Semantic"
        return result

    # Phase 4: code generation (TAC, then triples)
    result.tac = generate(result.tree)
    result.triples = to_triples(result.tac)

    # Phase 5: optimization (the original TAC is kept for the before/after view)
    result.optimized, result.changes = optimize(result.tac)
    return result