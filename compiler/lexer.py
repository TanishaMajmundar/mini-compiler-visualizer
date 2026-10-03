"""Phase 1: Lexical analysis (the lexer / scanner).

Input : source code as one string
Output: (list of Token, list of CompileError)

The lexer reads the source one character at a time and groups characters
into tokens (the smallest meaningful pieces: identifiers, numbers, operators).
It is written by hand: no regex library, no Lex/Flex.
"""

from dataclasses import dataclass

from compiler.errors import CompileError

# Words that have a special meaning in our language.
KEYWORDS = {"int", "float", "if", "else", "while"}

# Single-character tokens and their token type.
PUNCTUATION = {
    "(": "LPAREN",
    ")": "RPAREN",
    "{": "LBRACE",
    "}": "RBRACE",
    ";": "SEMI",
}

# Operators that are two characters long (must be checked before single ones).
TWO_CHAR_RELOPS = ("<=", ">=", "==", "!=")


@dataclass
class Token:
    """One token: its kind, the exact text, and where it appeared."""

    type: str     # KEYWORD, ID, NUM, OP, RELOP, ASSIGN, LPAREN, ..., EOF
    lexeme: str   # the exact text from the source, e.g. "count" or "+"
    line: int     # 1-based line number


def _is_letter(ch: str) -> bool:
    """True for a-z, A-Z and underscore (ASCII only)."""
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ch == "_"


def _is_digit(ch: str) -> bool:
    """True for 0-9 (ASCII only)."""
    return "0" <= ch <= "9"


def tokenize(source: str) -> tuple[list[Token], list[CompileError]]:
    """Convert source text into tokens.

    Invalid characters do not stop the scan: each one is recorded as an error
    and skipped, so we can report all lexical errors in one go.
    The returned token list always ends with an EOF token.
    """
    tokens: list[Token] = []
    errors: list[CompileError] = []
    i = 0              # position of the character we are looking at
    line = 1           # current line number
    n = len(source)

    while i < n:
        ch = source[i]

        # --- whitespace -------------------------------------------------
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch in " \t\r":
            i += 1
            continue

        # --- comment: // ... until end of line --------------------------
        if ch == "/" and i + 1 < n and source[i + 1] == "/":
            while i < n and source[i] != "\n":
                i += 1
            continue

        # --- identifier or keyword: letter (letter | digit)* ------------
        if _is_letter(ch):
            start = i
            while i < n and (_is_letter(source[i]) or _is_digit(source[i])):
                i += 1
            word = source[start:i]
            kind = "KEYWORD" if word in KEYWORDS else "ID"
            tokens.append(Token(kind, word, line))
            continue

        # --- number: digit+ [ . digit+ ] --------------------------------
        if _is_digit(ch):
            start = i
            while i < n and _is_digit(source[i]):
                i += 1
            if i < n and source[i] == ".":
                i += 1  # consume the '.'
                if i < n and _is_digit(source[i]):
                    while i < n and _is_digit(source[i]):
                        i += 1
                else:
                    # something like "3." with no digits after the dot
                    bad = source[start:i]
                    errors.append(
                        CompileError("Lexical", f"malformed number '{bad}'", line)
                    )
                    continue
            tokens.append(Token("NUM", source[start:i], line))
            continue

        # --- two-character relational operators: <= >= == != ------------
        two = source[i:i + 2]
        if two in TWO_CHAR_RELOPS:
            tokens.append(Token("RELOP", two, line))
            i += 2
            continue

        # --- single-character tokens ------------------------------------
        if ch in "+-*/":
            tokens.append(Token("OP", ch, line))
        elif ch in "<>":
            tokens.append(Token("RELOP", ch, line))
        elif ch == "=":
            tokens.append(Token("ASSIGN", ch, line))
        elif ch in PUNCTUATION:
            tokens.append(Token(PUNCTUATION[ch], ch, line))
        else:
            # Not part of our language: record the error and keep scanning.
            errors.append(CompileError("Lexical", f"invalid character '{ch}'", line))
        i += 1

    tokens.append(Token("EOF", "", line))
    return tokens, errors
