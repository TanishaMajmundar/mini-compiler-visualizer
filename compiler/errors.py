"""Shared error type used by every compiler phase.

One class keeps all error messages in the same format:
    Lexical error: invalid character '$' (line 1)
    Syntax error: expected ')' but found ';' (line 4)
"""


class CompileError(Exception):
    """An error found while compiling.

    phase   -> "Lexical", "Syntax" or (later) "Semantic"
    message -> what went wrong, e.g. "expected ')' but found ';'"
    line    -> 1-based line number in the source code
    """

    def __init__(self, phase: str, message: str, line: int) -> None:
        super().__init__(message)
        self.phase = phase
        self.message = message
        self.line = line

    def __str__(self) -> str:
        return f"{self.phase} error: {self.message} (line {self.line})"
