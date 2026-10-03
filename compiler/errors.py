"""Shared error type used by every compiler phase.

One class keeps all messages in the same format:
    Lexical error: invalid character '$' (line 1)
    Syntax error: expected ')' but found ';' (line 4)
    Semantic error: 'y' used before declaration (line 3)
    Semantic warning: float value assigned to int variable 'x' (line 2)
"""


class CompileError(Exception):
    """An error (or warning) found while compiling.

    phase    -> "Lexical", "Syntax" or "Semantic"
    message  -> what went wrong
    line     -> 1-based line number in the source code
    severity -> "error" stops compilation, "warning" does not
    """

    def __init__(self, phase: str, message: str, line: int, severity: str = "error") -> None:
        super().__init__(message)
        self.phase = phase
        self.message = message
        self.line = line
        self.severity = severity

    def __str__(self) -> str:
        return f"{self.phase} {self.severity}: {self.message} (line {self.line})"